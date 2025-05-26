from sqlalchemy import Column, DateTime, Integer, String

from database import Base


class Complaint(Base):
    """投诉数据模型"""

    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_time = Column(DateTime)
    content = Column(String)
    user_id = Column(String)
    complaint_category = Column(String)
    reply = Column(String)
