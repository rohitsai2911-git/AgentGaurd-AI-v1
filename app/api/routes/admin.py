from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import db_session, workspace_id
from app.services import seed as seed_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/seed", summary="Load seed data (idempotent)")
def load_seed(session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return {"status": "ok", **seed_service.load_seed(session, ws)}


@router.post("/seed/demo-runs", summary="Evaluate seeded cases with their known-good responses")
def seed_demo_runs(session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    created = seed_service.seed_demo_runs(session, ws)
    return {
        "status": "ok",
        "runs_created": created,
        "note": "Runs are produced by the real evaluation engine, not fixtures.",
    }


@router.delete("/seed", summary="Remove seeded data")
def remove_seed(session: Session = Depends(db_session), ws: str = Depends(workspace_id)):
    return {"status": "ok", **seed_service.remove_seed(session, ws)}