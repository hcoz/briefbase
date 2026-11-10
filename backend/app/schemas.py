from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
