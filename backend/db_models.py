"""
SQLAlchemy ORM models for persistence.

Tables: User, Report, ExtractedField
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    google_sub = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)

    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    source_type = Column(String, nullable=False, default="upload")  # "upload" | "edgar"
    ticker = Column(String, nullable=True)
    filename = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="reports")
    fields = relationship("ExtractedField", back_populates="report", cascade="all, delete-orphan")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    field_name = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    page_number = Column(Integer, nullable=True)
    source_text = Column(Text, nullable=True)
    extraction_method = Column(String, nullable=True)  # "regex" | "llm"
    confidence = Column(Float, nullable=True)

    report = relationship("Report", back_populates="fields")
