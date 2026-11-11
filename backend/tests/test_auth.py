from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings

PROTECTED_ROUTES = [
    ("GET", "/auth/me"),
    ("GET", "/notes"),
    ("POST", "/notes"),
    ("DELETE", "/notes/1"),
    ("POST", "/notes/1/summarize"),
]


def _claims(sub: str, *, expires_in: timedelta = timedelta(minutes=5)) -> dict:
    now = datetime.now(UTC)
    return {"sub": sub, "iat": now, "exp": now + expires_in}


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_login_and_me(client):
    r = client.post(
        "/auth/register", json={"email": "Alice@Example.com", "password": "password123"}
    )
    assert r.status_code == 201
    assert r.json()["token_type"] == "bearer"

    r = client.post("/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert r.status_code == 200

    r = client.get("/auth/me", headers=_bearer(r.json()["access_token"]))
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"  # stored lowercased


def test_token_carries_no_email(client, register):
    token = register()["Authorization"].removeprefix("Bearer ")
    payload = jwt.decode(token, options={"verify_signature": False})
    assert set(payload) == {"sub", "iat", "exp"}


def test_duplicate_email_returns_409(client, register):
    register("alice@example.com")
    r = client.post(
        "/auth/register", json={"email": "ALICE@example.com", "password": "password123"}
    )
    assert r.status_code == 409


def test_register_rejects_short_password(client):
    r = client.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert r.status_code == 422


@pytest.mark.parametrize(
    "email,password",
    [("alice@example.com", "wrong-password"), ("nobody@example.com", "password123")],
    ids=["wrong-password", "unknown-email"],
)
def test_bad_credentials_return_same_401(client, register, email, password):
    register("alice@example.com", "password123")
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


@pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
def test_protected_routes_require_token(client, method, path):
    r = client.request(method, path)
    assert r.status_code == 401
    assert r.json() == {"detail": "Invalid or expired token"}
    assert r.headers["WWW-Authenticate"] == "Bearer"


# Each case builds headers for an existing user id, so the 401 can only come
# from the token itself, not from a missing user.
BAD_TOKENS = {
    "garbage": lambda uid: _bearer("not-a-jwt"),
    "wrong-scheme": lambda uid: {"Authorization": f"Basic {uid}"},
    "wrong-secret": lambda uid: _bearer(
        jwt.encode(_claims(str(uid)), "some-other-secret-0123456789abcdef", algorithm="HS256")
    ),
    "alg-none": lambda uid: _bearer(jwt.encode(_claims(str(uid)), None, algorithm="none")),
    "expired": lambda uid: _bearer(
        jwt.encode(
            _claims(str(uid), expires_in=timedelta(minutes=-1)),
            settings.jwt_secret,
            algorithm="HS256",
        )
    ),
    "missing-exp": lambda uid: _bearer(
        jwt.encode({"sub": str(uid), "iat": datetime.now(UTC)}, settings.jwt_secret)
    ),
    "non-numeric-sub": lambda uid: _bearer(jwt.encode(_claims("abc"), settings.jwt_secret)),
    "unknown-user": lambda uid: _bearer(jwt.encode(_claims(str(uid + 999)), settings.jwt_secret)),
}


@pytest.mark.parametrize("make_headers", BAD_TOKENS.values(), ids=BAD_TOKENS.keys())
def test_invalid_tokens_return_401(client, register, make_headers):
    user_id = client.get("/auth/me", headers=register()).json()["id"]
    r = client.get("/notes", headers=make_headers(user_id))
    assert r.status_code == 401
    assert r.json() == {"detail": "Invalid or expired token"}
