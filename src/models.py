from sqlalchemy import Column, Integer, String, DateTime 
from .database import Base

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(String, nullable=True)
    created_at = Column(DateTime, index=True, nullable=False) 
    updated_at = Column(DateTime, index=True, nullable=False) 