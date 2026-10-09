from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.exceptions import EvaluationError
from app.evaluation.modules import accuracy, compliance, consistency, hallucination, safety
from app.evaluation.scoring import merge_results
from app.evaluation.types import Dimension, DimensionResult, TestCaseCriteria

logger = logging.getLogger(__name__)

PER_RESPONSE: dict[Dimension, Callable[[TestCaseCriteria, str], DimensionResult]] = {
    Dimension.ACCURACY: accuracy.evaluate_single,
    Dimension.HALLUCINATION: hallucination.evaluate_single,
    Dimension.SAFETY: safety.evaluate_single,
    Dimension.COMPLIANCE: compliance.evaluate_single,
}

WHOLE_SET: dict[Dimension, Callable[[TestCaseCriteria, list[str]], DimensionResult]] = {
    Dimension.CONSISTENCY: consistency.evaluate,
}

ORDER: list[Dimension] = [
    Dimension.ACCURACY,
    Dimension.HALLUCINATION,
    Dimension.SAFETY,
    Dimension.COMPLIANCE,
    Dimension.CONSISTENCY,
]


def methodology_for(dimension: Dimension) -> str:
    if dimension is Dimension.CONSISTENCY:
        return (
            f"{consistency.METHODOLOGY_CROSS} {consistency.METHODOLOGY_INTERNAL}"
        )
    module = (
        PER_RESPONSE[dimension].__module__
        if dimension in PER_RESPONSE
        else WHOLE_SET[dimension].__module__
    )
    import importlib

    return getattr(importlib.import_module(module), "METHODOLOGY", "")


def enabled_dimensions(criteria: TestCaseCriteria) -> list[Dimension]:
    requested = {d.value for d in Dimension}
    configured = set(criteria.enabled_dimensions or [])
    selected = configured & requested if configured else requested
    return [d for d in ORDER if d in selected]


def run_dimensions(
    criteria: TestCaseCriteria, responses: list[str]
) -> list[DimensionResult]:
    if not responses:
        raise EvaluationError("At least one agent response is required to evaluate.")

    results: list[DimensionResult] = []
    for dimension in enabled_dimensions(criteria):
        try:
            if dimension in WHOLE_SET:
                result = WHOLE_SET[dimension](criteria, responses)
            else:
                per_response = []
                for index, response in enumerate(responses):
                    single = PER_RESPONSE[dimension](criteria, response)
                    for finding in single.findings:
                        finding.response_index = index
                    per_response.append(single)
                result = merge_results(per_response) if len(per_response) > 1 else per_response[0]
        except EvaluationError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Dimension %s failed for test case %s", dimension.value, criteria.name)
            raise EvaluationError(
                f"Evaluation module '{dimension.value}' failed: {exc}",
                details={"dimension": dimension.value, "test_case": criteria.name},
            ) from exc
        results.append(result)
    return results


def all_findings(results: list[DimensionResult]) -> list:
    return [f for r in results for f in r.findings]