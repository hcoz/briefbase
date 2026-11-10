from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY  # PG ARRAY supports .contains() -> @>
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)  # stored lowercased
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        # List query: WHERE user_id = ? ORDER BY created_at DESC, id DESC.
        # id is a tie-breaker so the order is always deterministic; having it in
        # the index means rows come out pre-sorted (no sort step).
        # Leading column is user_id, so this also serves plain user_id lookups
        # (ownership checks, FK cascade) — no separate user_id index needed.
        Index(
            "ix_notes_user_id_created_at",
            "user_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        # Tag filter: tags @> ARRAY[?]
        Index("ix_notes_tags", "tags", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
