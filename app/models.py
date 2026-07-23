"""SQLAlchemy ORM models for the Requirement Intelligence Assistant.

Tables:
- projects: uploaded document metadata (one row per upload)
- jobs: analysis pipeline execution records (one row per /analyze call)
"""
from datetime import datetime, timezone
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class Project(Base):
    """One row per uploaded document."""

    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False, default="Untitled")
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    section_count: Mapped[int] = mapped_column(Integer, default=0)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationship
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "filename": self.filename,
            "title": self.title,
            "version": self.version,
            "section_count": self.section_count,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

class Job(Base):
    """One row per /analyze call — tracks pipeline status."""

    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    project: Mapped["Project"] = relationship("Project", back_populates="jobs")

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
