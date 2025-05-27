from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from utils.config import SQLALCHEMY_DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Complaint(Base):
    """投诉数据模型"""

    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_time = Column(DateTime)
    content = Column(String)
    user_id = Column(String)
    complaint_category = Column(String)
    reply = Column(String)
