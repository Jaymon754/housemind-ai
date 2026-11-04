"""SQLAlchemy persistence. SQLite by default; MySQL via DATABASE_URL."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import ROOT, settings


def _normalise_url(url: str) -> str:
    if url.startswith("sqlite:///./"):
        path = ROOT / url.removeprefix("sqlite:///./")
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"
    return url


DATABASE_URL = _normalise_url(settings.database_url)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(120), default="新的房产分析")
    mode: Mapped[str] = mapped_column(String(24), default="local")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(24), default="local")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class ToolEvent(Base):
    __tablename__ = "tool_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(64))
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SavedAnalysis(Base):
    __tablename__ = "saved_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(160))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
