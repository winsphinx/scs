import logging
import random
from datetime import datetime
from typing import Dict, List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker

from llm_service import ComplaintAnalyzer
from models import Base, Complaint
from config import SIMULATION_CONFIG

app = FastAPI()
# 配置中间件和静态文件
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# 数据库配置
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/complaints.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base 类已从 models.py 导入


# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


@app.get("/")
async def read_index():
    return FileResponse("templates/index.html")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ComplaintCreate(BaseModel):
    complaint_time: datetime
    content: str
    user_id: str
    complaint_category: str
    reply: str | None = None


class ComplaintResponse(ComplaintCreate):
    id: int
    complaint_time: datetime

    class Config:
        from_attributes = True


@app.post("/complaints/", response_model=ComplaintResponse)
def create_complaint(complaint: ComplaintCreate, db: Session = Depends(get_db)):
    db_complaint = Complaint(**complaint.model_dump())
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint


@app.get("/complaints/", response_model=List[ComplaintResponse])
def read_complaints(
    q: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    analyzer: ComplaintAnalyzer = Depends(lambda: ComplaintAnalyzer()),
):
    base_query = db.query(Complaint)

    if q:
        try:
            filter_condition = analyzer.query_parser_chain.invoke({"query": q}).content
            if filter_condition:
                logger.info(f"Parsed query condition: {filter_condition}")

                from sqlalchemy import and_, not_, or_

                safe_dict = {
                    "and_": and_,
                    "or_": or_,
                    "not_": not_,
                    "Complaint": Complaint,
                    "datetime": datetime,
                    "complaint_category": Complaint.complaint_category,
                    "content": Complaint.content,
                    "user_id": Complaint.user_id,
                    "complaint_time": Complaint.complaint_time,
                    "reply": Complaint.reply,
                    "contains": lambda field, value: field.contains(value),
                }
                compiled_condition = compile(filter_condition, "<string>", "eval")
                for name in compiled_condition.co_names:
                    if name not in safe_dict:
                        raise ValueError(f"Unsafe expression: {name}")
                condition = eval(compiled_condition, {"__builtins__": None}, safe_dict)
                base_query = base_query.filter(condition)
        except Exception as e:
            logger.error(f"Query parsing failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"查询解析失败: {str(e)}")

    complaints = base_query.offset(skip).limit(limit).all()
    return complaints


@app.get("/complaints/{complaint_id}", response_model=ComplaintCreate)
def read_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@app.put("/complaints/{complaint_id}", response_model=ComplaintCreate)
def update_complaint(
    complaint_id: int, complaint: ComplaintCreate, db: Session = Depends(get_db)
):
    db_complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if db_complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    for key, value in complaint.model_dump().items():
        setattr(db_complaint, key, value)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint


@app.delete("/complaints/{complaint_id}")
def delete_complaint(complaint_id: int, db: Session = Depends(get_db)):
    db_complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if db_complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    db.delete(db_complaint)
    db.commit()
    return {"message": "Complaint deleted"}


@app.get("/statistics/", response_model=Dict[str, int])
def get_statistics(db: Session = Depends(get_db)):
    statistics = (
        db.query(Complaint.complaint_category, func.count(Complaint.id))
        .group_by(Complaint.complaint_category)
        .order_by(func.count(Complaint.id).desc())
        .all()
    )
    return dict(statistics)


@app.post("/simulate/", response_model=List[ComplaintCreate])
def simulate_data(db: Session = Depends(get_db)):
    config = SIMULATION_CONFIG
    complaints = []
    for _ in range(10):
        category = random.choice(config["categories"])
        problem = random.choice(config["problems"][category])
        complaint = Complaint(
            complaint_time=datetime.now(),
            content=f"我的{category}{problem}" if category != "未知" else problem,
            user_id=f"user_{random.randint(1, 1000):04d}",
            complaint_category=category,
            reply=(
                random.choice(config["replies"]) if random.random() > 0.7 else None
            ),  # 30%概率有回复
        )
        db.add(complaint)
        complaints.append(complaint)
        logger.info(f"Generated simulated complaint: {complaint.content}")
    db.commit()
    return complaints


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
