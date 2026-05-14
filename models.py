from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import uuid


class Document(Base):
    __tablename__ = "documents"

    id         = Column(UNIQUEIDENTIFIER, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename   = Column(String(255), nullable=False)
    file_type  = Column(String(10),  nullable=False)
    num_chunks = Column(Integer,     nullable=False)
    created_at = Column(DateTime,    default=datetime.utcnow)

    questions  = relationship(
        "Question",
        back_populates="document",
        cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id          = Column(UNIQUEIDENTIFIER, primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id      = Column(UNIQUEIDENTIFIER, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    type        = Column(String(10),  nullable=False)
    question    = Column(Text,        nullable=False)
    options     = Column(Text,        nullable=True)
    answer      = Column(String(10),  nullable=True)
    explanation = Column(Text,        nullable=True)
    key_points  = Column(Text,        nullable=True)
    created_at  = Column(DateTime,    default=datetime.utcnow)

    document = relationship("Document", back_populates="questions")
