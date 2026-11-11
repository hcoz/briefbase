from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.db import DbSession
from app.models import User
from app.schemas import LoginIn, RegisterIn, Token, UserOut
from app.security import (
    BEARER_HEADERS,
    CurrentUser,
    authenticate_user,
    create_access_token,
    hash_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: DbSession) -> Token:
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # unique index on email; also safe under concurrent signups
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    return Token(access_token=create_access_token(user.id))


@router.post("/login")
def login(body: LoginIn, db: DbSession) -> Token:
    user = authenticate_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers=BEARER_HEADERS,
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
