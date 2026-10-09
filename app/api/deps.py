from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.db.models import User, Workspace
from app.db.session import get_session
from app.services import analytics_service, auth_service, evaluation_service, suite_service, test_case_service


def db_session(session: Session = Depends(get_session)) -> Session:
    return session


def settings_dep(settings: Settings = Depends(get_settings)) -> Settings:
    return settings


def test_cases(session: Session = Depends(db_session)):
    return test_case_service


def evaluations(session: Session = Depends(db_session)):
    return evaluation_service


def suites(session: Session = Depends(db_session)):
    return suite_service


def analytics(session: Session = Depends(db_session)):
    return analytics_service


def database_ok(session: Session = Depends(db_session)) -> bool:
    try:
        session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# Auth / multi-tenancy
# --------------------------------------------------------------------------


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(db_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = auth_service.decode_token(token)
    except Exception:
        raise AuthenticationError("Invalid or expired token.")
    user_id = payload.get("sub")
    user = session.get(User, user_id) if user_id else None
    if user is None:
        raise AuthenticationError("User no longer exists.")
    return user


def get_current_workspace(
    user: User = Depends(get_current_user),
    session: Session = Depends(db_session),
) -> Workspace:
    workspace = auth_service.primary_workspace(session, user)
    if workspace is None:
        raise AuthenticationError("No workspace for this account.")
    return workspace


def workspace_id(workspace: Workspace = Depends(get_current_workspace)) -> str:
    return workspace.id