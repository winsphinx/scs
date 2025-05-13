from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    category = Column(String(50), nullable=False)
    source = Column(String(100), default="http://xyz.net")


class DatabaseManager:
    def __init__(self, db_name="complaint.db"):
        self.engine = create_engine(f"sqlite:///{db_name}")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_complaint(self, title, content, category):
        complaint = Complaint(title=title, content=content, category=category)
        self.session.add(complaint)
        self.session.commit()
        return complaint.id

    def get_all_complaints(self):
        return self.session.query(Complaint).all()

    def get_complaint_by_id(self, complaint_id):
        return (
            self.session.query(Complaint).filter(Complaint.id == complaint_id).first()
        )

    def update_complaint(self, complaint_id, **kwargs):
        complaint = self.get_complaint_by_id(complaint_id)
        if complaint:
            for key, value in kwargs.items():
                setattr(complaint, key, value)
            self.session.commit()
            return True
        return False

    def delete_complaint(self, complaint_id):
        complaint = self.get_complaint_by_id(complaint_id)
        if complaint:
            self.session.delete(complaint)
            self.session.commit()
            return True
        return False
