from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.constants import (
    CONTENT_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    TITLE_MAX_LENGTH,
)

# --- Auth --------------------------------------------------------------------


class _EmailIn(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase(cls, v: str) -> str:
        return v.lower()  # emails are stored and looked up lowercased


class RegisterIn(_EmailIn):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class LoginIn(_EmailIn):
    # No min_length here: a policy change must not lock out existing users,
    # and a too-short password should get the same 401 as a wrong one.
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


# --- Notes -------------------------------------------------------------------


class NoteIn(BaseModel):
    # Blank or whitespace-only title -> None (matches the nullable column).
    title: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=TITLE_MAX_LENGTH)] | None
    ) = None
    content: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=CONTENT_MAX_LENGTH),
    ]

    @field_validator("title")
    @classmethod
    def blank_title_is_none(cls, v: str | None) -> str | None:
        return v or None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    content: str
    summary: str | None
    tags: list[str]
    created_at: datetime
