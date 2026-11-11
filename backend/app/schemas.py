from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

# --- Auth --------------------------------------------------------------------


class _EmailIn(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def lowercase(cls, v: str) -> str:
        return v.lower()  # emails are stored and looked up lowercased


class RegisterIn(_EmailIn):
    # max_length caps the work argon2 does on an attacker-supplied input.
    password: str = Field(min_length=8, max_length=128)


class LoginIn(_EmailIn):
    # No min_length here: a policy change must not lock out existing users,
    # and a too-short password should get the same 401 as a wrong one.
    password: str = Field(max_length=128)


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
    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    # max_length matches ai.MAX_INPUT_CHARS and the textarea limit in NoteForm.tsx.
    content: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000)
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
