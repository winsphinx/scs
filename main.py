import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from services.llm import ComplaintAnalyzer
from utils.config import SIMULATION_CONFIG
from utils.db import Base, Complaint, SessionLocal, engine
from utils.logging import configure_logging

# 配置日志
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="templates/static"), name="static")

Base.metadata.create_all(bind=engine)


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

    class Config:
        from_attributes = True


@app.get("/")
async def read_index():
    return FileResponse("templates/index.html")


@app.post("/complaints/", response_model=ComplaintResponse)
def create_complaint(complaint: ComplaintCreate, db: Session = Depends(get_db)):
    db_complaint = Complaint(**complaint.model_dump())
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint


@app.get("/complaints/", response_model=List[ComplaintResponse])
def read_complaints(
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    analyzer: ComplaintAnalyzer = Depends(lambda: ComplaintAnalyzer()),
):
    base_query = db.query(Complaint)

    if q:
        try:
            filter_condition = analyzer.query_parser_chain.invoke({"query": q})
            if filter_condition and filter_condition.strip():
                logger.info(f"Parsed query condition: {filter_condition}")

                try:
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
                    if not isinstance(filter_condition, str):
                        raise ValueError("Filter condition must be a string")
                    compiled_condition = compile(
                        str(filter_condition), "<string>", "eval"
                    )
                    for name in compiled_condition.co_names:
                        if name not in safe_dict:
                            raise ValueError(f"Unsafe expression: {name}")
                    condition = eval(
                        compiled_condition, {"__builtins__": None}, safe_dict
                    )
                    base_query = base_query.filter(condition)
                except Exception as e:
                    logger.warning(
                        f"Query parsing failed, falling back to simple search: {str(e)}"
                    )
                    # 查询解析失败时回退到简单搜索
                    base_query = base_query.filter(
                        Complaint.content.contains(q)
                        | Complaint.complaint_category.contains(q)
                    )
        except Exception as e:
            logger.warning(f"查询解析失败: {str(e)}")

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
    return {category: count for category, count in statistics}


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


@app.post("/analyze/")
def analyze_complaint(
    request: Dict[str, Any],
    analyzer: ComplaintAnalyzer = Depends(lambda: ComplaintAnalyzer()),
):
    """分析投诉内容并返回处理方法"""
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="投诉内容不能为空")

        result = analyzer.analyze(text)
        logger.info(f"Analyzer category: {result.category}, reply: {result.reply}")
        return {
            "category": result.category,
            "reply": result.reply,
            "suggestion": f"{result.reply}",  # 添加AI建议的处理方法
        }
    except Exception as e:
        logger.error(f"Error in analyze_complaint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
