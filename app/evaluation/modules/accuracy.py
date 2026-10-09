from __future__ import annotations

from app.evaluation.normalize import (
    contains_phrase,
    extract_numbers,
    jaccard,
    normalize_text,
    token_set,
    truncate,
)
from app.evaluation.scoring import clamp
from app.evaluation.types import (
    Dimension,
    DimensionResult,
    Finding,
    Severity,
    TestCaseCriteria,
    Verification,
)

METHODOLOGY = (
    "Weighted match against expected_answer: token-set Jaccard similarity (0.50), "
    "required-keyword coverage (0.30), expected-numeric presence (0.20). "
    "A forbidden keyword caps the score at 40 and forces a failure."
)

FORBIDDEN_CAP = 40
SIMILARITY_WEIGHT = 0.50
KEYWORD_WEIGHT = 0.30
NUMERIC_WEIGHT = 0.20


def evaluate_single(criteria: TestCaseCriteria, response: str) -> DimensionResult:
    if not response or not response.strip():
        return DimensionResult(
            dimension=Dimension.ACCURACY,
            score=0,
            passed=False,
            severity=Severity.HIGH,
            findings=[
                Finding(
                    rule_id="ACC_EMPTY_RESPONSE",
                    dimension=Dimension.ACCURACY,
                    severity=Severity.HIGH,
                    verification=Verification.VERIFIED,
                    message="The agent returned an empty response.",
                    evidence="",
                    remediation=(
                        "Investigate why the agent produced no output before evaluating "
                        "any other dimension."
                    ),
                )
            ],
            methodology=METHODOLOGY,
            details={
                "similarity": 0.0,
                "required_keywords_total": len(criteria.required_keywords),
                "required_keywords_covered": 0,
                "keyword_coverage": 0.0,
                "expected_numbers_total": len(criteria.expected_numbers),
                "expected_numbers_found": 0,
                "numeric_match": 0.0,
                "forbidden_hits": 0,
                "threshold": criteria.threshold_for(Dimension.ACCURACY),
                "score_capped": False,
            },
            forced_fail=True,
        )

    normalized_response = normalize_text(response)
    response_tokens = token_set(response)
    expected_tokens = token_set(criteria.expected_answer)

    similarity = jaccard(response_tokens, expected_tokens)

    required = criteria.required_keywords
    covered = [k for k in required if contains_phrase(normalized_response, k)]
    missing = [k for k in required if k not in covered]
    coverage = (len(covered) / len(required)) if required else 1.0

    expected_numbers = [float(n) for n in criteria.expected_numbers]
    response_numbers = extract_numbers(response)
    if expected_numbers:
        found = [n for n in expected_numbers if any(_close(n, m) for m in response_numbers)]
        numeric_match = len(found) / len(expected_numbers)
        missing_numbers = [n for n in expected_numbers if n not in found]
    else:
        numeric_match = 1.0
        found = []
        missing_numbers = []

    score = clamp(
        similarity * SIMILARITY_WEIGHT * 100
        + coverage * KEYWORD_WEIGHT * 100
        + numeric_match * NUMERIC_WEIGHT * 100
    )

    findings: list[Finding] = []

    if missing:
        findings.append(
            Finding(
                rule_id="ACC_MISSING_REQUIRED_KEYWORD",
                dimension=Dimension.ACCURACY,
                severity=Severity.MEDIUM,
                verification=Verification.VERIFIED,
                message=(
                    f"{len(missing)} required term(s) absent from the response: "
                    + ", ".join(missing[:8])
                ),
                evidence=truncate(response),
                remediation=(
                    "Add the missing expected concepts to the agent response, or "
                    "remove them from required_keywords if they are genuinely optional."
                ),
            )
        )

    if missing_numbers:
        findings.append(
            Finding(
                rule_id="ACC_MISSING_EXPECTED_NUMBER",
                dimension=Dimension.ACCURACY,
                severity=Severity.HIGH,
                verification=Verification.VERIFIED,
                message="Expected numeric value(s) not present in the response: "
                + ", ".join(_fmt(n) for n in missing_numbers[:8]),
                evidence=truncate(response),
                remediation=(
                    "State the correct figures explicitly. Wrong or omitted numbers are "
                    "the most common source of customer-facing errors."
                ),
            )
        )

    forbidden_hits = [
        k for k in criteria.forbidden_keywords if contains_phrase(normalized_response, k)
    ]
    forced_fail = False
    if forbidden_hits:
        forced_fail = True
        score = min(score, FORBIDDEN_CAP)
        findings.append(
            Finding(
                rule_id="ACC_FORBIDDEN_CONTENT",
                dimension=Dimension.ACCURACY,
                severity=Severity.HIGH,
                verification=Verification.VERIFIED,
                message="Forbidden content present: " + ", ".join(forbidden_hits[:8]),
                evidence=truncate(response),
                remediation=(
                    "Remove the forbidden phrasing. These terms are excluded because "
                    "the agent must never assert them for this scenario."
                ),
            )
        )

    threshold = criteria.threshold_for(Dimension.ACCURACY)
    passed = score >= threshold and not forced_fail
    if not passed and not findings:
        findings.append(
            Finding(
                rule_id="ACC_BELOW_THRESHOLD",
                dimension=Dimension.ACCURACY,
                severity=Severity.MEDIUM,
                verification=Verification.VERIFIED,
                message=f"Accuracy score {score} is below the configured threshold {threshold}.",
                evidence=truncate(response),
                remediation="Align the response more closely with the expected answer.",
            )
        )

    return DimensionResult(
        dimension=Dimension.ACCURACY,
        score=score,
        passed=passed,
        severity=_worst(findings),
        findings=findings,
        methodology=METHODOLOGY,
        details={
            "similarity": round(similarity, 4),
            "required_keywords_total": len(required),
            "required_keywords_covered": len(covered),
            "keyword_coverage": round(coverage, 4),
            "expected_numbers_total": len(expected_numbers),
            "expected_numbers_found": len(found),
            "numeric_match": round(numeric_match, 4),
            "forbidden_hits": len(forbidden_hits),
            "threshold": threshold,
            "score_capped": bool(forbidden_hits),
        },
        forced_fail=forced_fail,
    )


def _close(a: float, b: float, tolerance: float = 1e-6) -> bool:
    return abs(a - b) <= tolerance


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def _worst(findings: list[Finding]) -> Severity:
    if not findings:
        return Severity.NONE
    order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    return next(s for s in order if any(f.severity == s for f in findings))