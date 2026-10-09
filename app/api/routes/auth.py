from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, get_current_workspace
from app.core.exceptions import AuthenticationError
from app.db.models import User, Workspace
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    TokenResponse,
    UserRead,
    WorkspaceRead,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, summary="Create an account and workspace")
def register(payload: RegisterRequest, session: Session = Depends(db_session)):
    user, workspace = auth_service.register(
        session,
        email=payload.email,
        password=payload.password,
        name=payload.name,
        workspace_name=payload.workspace_name,
    )
    return TokenResponse(
        access_token=auth_service.create_token(user),
        user=UserRead.model_validate(user),
        workspace=WorkspaceRead.model_validate(workspace),
    )


@router.post("/login", response_model=TokenResponse, summary="Log in")
def login(payload: LoginRequest, session: Session = Depends(db_session)):
    user = auth_service.authenticate(session, payload.email, payload.password)
    workspace = auth_service.primary_workspace(session, user)
    if workspace is None:
        raise AuthenticationError("No workspace for this account.")
    return TokenResponse(
        access_token=auth_service.create_token(user),
        user=UserRead.model_validate(user),
        workspace=WorkspaceRead.model_validate(workspace),
    )


@router.get("/me", response_model=MeResponse, summary="Current user and workspace")
def me(
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    return MeResponse(
        user=UserRead.model_validate(user),
        workspace=WorkspaceRead.model_validate(workspace),
    )