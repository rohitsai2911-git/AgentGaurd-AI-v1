from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

# Bump when the schema changes in a way that needs a rebuild.
SCHEMA_VERSION = 2

_connect_args: dict[str, object] = {}
if _settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    _settings.database_url,
    connect_args=_connect_args,
    future=True,
)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    if _settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _user_version() -> int:
    with engine.connect() as conn:
        return int(conn.execute(text("PRAGMA user_version")).scalar() or 0)


def _set_user_version(value: int) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"PRAGMA user_version = {int(value)}"))


def init_db() -> None:
    from app.db import models  # noqa: F401  (register mappers)

    from app.db.base import Base

    Base.metadata.create_all(bind=engine)

    if _user_version() < SCHEMA_VERSION:
        # One-time migration to the multi-tenant schema: workspace_id columns,
        # per-workspace unique names, and the users/workspaces tables. Rebuild
        # from the current models. Seed data is reproducible and re-created in
        # _bootstrap(), so nothing the engine needs is lost.
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        _set_user_version(SCHEMA_VERSION)
        _bootstrap()


def _bootstrap() -> None:
    """Create a demo account + workspace and seed it so the app is never empty."""
    from app.db.models import Workspace
    from app.services import auth_service, seed as seed_service

    with SessionLocal() as session:
        if session.query(Workspace).first() is not None:
            return
        try:
            _user, workspace = auth_service.register(
                session,
                email="demo@agentguard.local",
                password="demo1234",
                name="Demo Owner",
                workspace_name="Demo Workspace",
            )
        except Exception:
            session.rollback()
            return
        try:
            seed_service.load_seed(session, workspace_id=workspace.id)
            seed_service.seed_demo_runs(session, workspace_id=workspace.id)
        except Exception:
            session.rollback()


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()