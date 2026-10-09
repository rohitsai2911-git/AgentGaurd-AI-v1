from __future__ import annotations

from fastapi import APIRouter

from app.evaluation.modules.compliance import VALIDATORS
from app.evaluation.modules.consistency import METHODOLOGY_CROSS, METHODOLOGY_INTERNAL
from app.evaluation.modules.safety import catalogue
from app.evaluation.registry import ORDER, methodology_for
from app.evaluation.scoring import default_thresholds, default_weights
from app.evaluation.types import (
    HALLUCINATION_DISCLAIMER,
    ConstraintType,
    Dimension,
    Severity,
)

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/dimensions", summary="Dimensions, weights, thresholds and methodology")
def dimensions():
    return {
        "dimensions": [
            {
                "dimension": d.value,
                "default_weight": default_weights()[d.value],
                "default_threshold": default_thresholds()[d.value],
                "methodology": methodology_for(d),
            }
            for d in ORDER
        ],
        "evaluation_order": [d.value for d in ORDER],
        "severity_levels": [s.value for s in Severity],
        "scoring_rule": (
            "overall_score = weighted mean of enabled dimension scores, weights "
            "renormalised over the dimensions actually evaluated. The verdict is a hard "
            "gate: PASS requires every enabled dimension to pass and zero critical "
            "findings, so a high score can never mask a critical failure."
        ),
        "disclaimer": HALLUCINATION_DISCLAIMER,
    }


@router.get("/safety-rules", summary="Safety rule catalogue")
def safety_rules():
    return {"rules": catalogue(), "count": len(catalogue())}


@router.get("/constraint-types", summary="Instruction compliance constraint types")
def constraint_types():
    return {
        "constraint_types": [
            {
                "type": c.value,
                "requires_value": c
                in {ConstraintType.MAX_WORDS, ConstraintType.MIN_WORDS},
                "requires_phrases": c
                in {ConstraintType.MUST_INCLUDE, ConstraintType.MUST_EXCLUDE},
            }
            for c in ConstraintType
        ],
        "count": len(VALIDATORS),
    }


@router.get("/consistency-modes", summary="Consistency evaluation modes")
def consistency_modes():
    return {
        "modes": [
            {
                "mode": "cross_response",
                "trigger": "two or more responses submitted",
                "methodology": METHODOLOGY_CROSS,
            },
            {
                "mode": "internal",
                "trigger": "exactly one response submitted",
                "methodology": METHODOLOGY_INTERNAL,
            },
        ]
    }


@router.get("/disclaimer", summary="Heuristic-detection disclaimer")
def disclaimer():
    return {
        "disclaimer": HALLUCINATION_DISCLAIMER,
        "verified_means": "Provable against the test case's grounding source.",
        "risk_means": "A heuristic indicator that requires human review.",
        "dimensions": [d.value for d in Dimension],
    }


@router.get("/llm-status", summary="Optional LLM judge availability (key never exposed)")
def llm_status():
    from app.evaluation.llm import status_payload

    payload = status_payload()
    payload["usage"] = (
        "Pass use_llm=true to POST /api/v1/evaluations/run|preview for "
        "deterministic + advisory LLM, or call POST "
        "/api/v1/evaluations/llm-evaluate for LLM-only output."
    )
    return payload


@router.get("/laya-status", summary="Optional Laya judge availability and config")
def laya_status():
    from app.evaluation.laya import status_payload

    payload = status_payload()
    payload["usage"] = (
        "Pass use_laya=true to POST /api/v1/evaluations/run|preview for "
        "deterministic + advisory Laya decisions, or call POST "
        "/api/v1/evaluations/laya-evaluate for Laya-only output. "
        "Pipeline order: deterministic -> Laya -> OpenRouter -> aggregate. "
        "Advisory judges never alter deterministic verdict/scores."
    )
    return payload