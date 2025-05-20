from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from llm_service import ComplaintAnalyzer
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from datetime import datetime
from typing import List, Dict
import random

from fastapi.staticfiles import StaticFiles

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
SQLALCHEMY_DATABASE_URL = "sqlite:///./complaints.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True, index=True)
    complaint_time = Column(DateTime)
    content = Column(String)
    user_id = Column(String)
    complaint_category = Column(String)
    reply = Column(String)


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
        orm_mode = True


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
            filter_condition = analyzer.query_parser_chain.run(query=q)
            if filter_condition:
                base_query = base_query.filter(eval(filter_condition))
        except Exception as e:
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
    for key, value in complaint.dict().items():
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
    categories = ["各种电视", "冰箱冰柜", "洗衣机", "未知"]
    replies = [
        "已处理",
        "正在处理中",
        "已转交相关部门",
        None,
        None,
    ]  # 增加None使部分投诉无回复
    complaints = []
    for _ in range(10):  # 模拟10条数据
        product = random.choice(categories)
        complaint = Complaint(
            complaint_time=datetime.now(),
            content=f"我的{product}有问题" if product != "未知" else "产品使用问题投诉",
            user_id=f"user_{random.randint(1, 100)}",
            complaint_category=product,
            reply=(
                random.choice(replies) if random.random() > 0.3 else None
            ),  # 70%概率有回复
        )
        db.add(complaint)
        complaints.append(complaint)
    db.commit()
    return complaints


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
