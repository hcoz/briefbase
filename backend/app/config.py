from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a .env file).

    DATABASE_URL and JWT_SECRET have no defaults: the app refuses to start
    without them.
    """

    model_config = SettingsConfigDict(
        # Root .env when run from backend/ locally; in Docker/Railway the
        # variables are injected into the environment directly.
        env_file=("../.env", ".env"),
        extra="ignore",
        hide_input_in_errors=True,  # don't echo secrets in startup errors
    )

    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_expire_minutes: int = 60

    gemini_api_key: str = ""  # empty -> AI treated as unavailable
    gemini_model: str = "gemini-2.5-flash"

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, v: str) -> str:
        # Railway (and Heroku-style hosts) inject postgres:// or postgresql://.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v.removeprefix(prefix)
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


settings = Settings()
