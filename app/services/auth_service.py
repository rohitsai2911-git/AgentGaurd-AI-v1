"""Authentication + workspace bootstrap.

Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib, no native deps).
Tokens are JWTs signed with HS256 (stdlib hmac backend — no cryptography dep).
Advisory judges (LLM/Laya) are unrelated to this; auth only gates data access.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import EmailTakenError, InvalidCredentialsError
from app.db.models import User, Workspace

_PBKDF2_ROUNDS = 120_000


def _hash_password(password: str, salt: str) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ROUNDS
    )
    return derived.hex()


def register(
    session: Session,
    email: str,
    password: str,
    name: str = "",
    workspace_name: str = "My Workspace",
) -> tuple[User, Workspace]:
    email = (email or "").strip().lower()
    if "@" not in email:
        raise InvalidCredentialsError("Enter a valid email address.")
    if len(password or "") < 8:
        raise InvalidCredentialsError("Password must be at least 8 characters.")
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise EmailTakenError(f"An account for '{email}' already exists.")

    salt = secrets.token_hex(16)
    user = User(
        email=email,
        name=(name or "").strip() or email.split("@")[0],
        password_hash=_hash_password(password, salt),
        salt=salt,
    )
    session.add(user)
    session.flush()  # assign user.id before creating the workspace
    workspace = Workspace(
        name=(workspace_name or "").strip() or "My Workspace", owner_id=user.id
    )
    session.add(workspace)
    session.commit()
    session.refresh(user)
    session.refresh(workspace)
    return user, workspace


def authenticate(session: Session, email: str, password: str) -> User:
    email = (email or "").strip().lower()
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        raise InvalidCredentialsError("Incorrect email or password.")
    expected = _hash_password(password or "", user.salt)
    if not hmac.compare_digest(expected, user.password_hash):
        raise InvalidCredentialsError("Incorrect email or password.")
    return user


def create_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "email": user.email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def primary_workspace(session: Session, user: User) -> Workspace | None:
    return session.scalar(
        select(Workspace)
        .where(Workspace.owner_id == user.id)
        .order_by(Workspace.created_at)
    )


__all__ = [
    "authenticate",
    "create_token",
    "decode_token",
    "primary_workspace",
    "register",
]