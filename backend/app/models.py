from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY  # PG ARRAY supports .contains() -> @>
from sqlalchemy.orm import Mapped, mapped_column

from app.constants import EMAIL_MAX_LENGTH, PASSWORD_HASH_MAX_LENGTH, TITLE_MAX_LENGTH
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored lowercased.
    email: Mapped[str] = mapped_column(String(EMAIL_MAX_LENGTH), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(PASSWORD_HASH_MAX_LENGTH))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        # List query: WHERE user_id = ? ORDER BY created_at DESC, id DESC.
        # id is a tie-breaker so the order is always deterministic; having it in
        # the index means rows come out pre-sorted (no sort step).
        # Leading column is user_id, so this also covers the FK cascade
        # (DELETE ... WHERE user_id = ?); no separate user_id index needed.
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
    title: Mapped[str | None] = mapped_column(String(TITLE_MAX_LENGTH))
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
