from __future__ import annotations

from collections.abc import Callable

from app.evaluation.normalize import (
    contains_phrase,
    jaccard,
    normalize_text,
    token_set,
    truncate,
    word_count,
)
from app.evaluation.types import (
    Constraint,
    ConstraintType,
    Dimension,
    DimensionResult,
    Finding,
    Severity,
    TestCaseCriteria,
    Verification,
)

METHODOLOGY = (
    "Evaluates the declarative constraint list declared on the test case. Each "
    "constraint type maps to an independent validator, so adding a constraint type "
    "requires no change to this module. Score = 100 - 100 * (violations / constraints)."
)

VIOLATION_PENALTY = 25
ENGLISH_ASCII_THRESHOLD = 0.85
SHOUT_THRESHOLD = 0.30

Validator = Callable[[Constraint, str, TestCaseCriteria], str | None]


def _v_max_words(c: Constraint, text: str, tc: TestCaseCriteria) -> str | None:
    limit = int(c.value or 0)
    count = word_count(text)
    if count > limit:
        return f"Response is {count} words, exceeding the {limit}-word limit"
    return None


def _v_min_words(c: Constraint, text: str, tc: TestCaseCriteria) -> str | None:
    limit = int(c.value or 0)
    count = word_count(text)
    if count < limit:
        return f"Response is {count} words, below the {limit}-word minimum"
    return None


def _v_must_include(c: Constraint, text: str, tc: TestCaseCriteria) -> str | None:
    norm = normalize_text(text)
    missing = [p for p in c.phrases if not contains_phrase(norm, p)]
    if missing:
        return "Required phrase(s) missing: " + ", ".join(missing[:8])
    return None


def _v_must_exclude(c: Constraint, text: str, tc: TestCaseCriteria) -> str | None:
    norm = normalize_text(text)
    present = [p for p in c.phrases if contains_phrase(norm, p)]
    if present:
        return "Forbidden phrase(s) present: " + ", ".join(present[:8])
    return None


def _v_must_answer_prompt(c: Constraint, text: str, tc: TestCaseCriteria) -> str | None:
    similarity = jaccard(token_set(text), token_set(tc.input_prompt))
    if similarity < 0.05:
        return (
            "Response shares almost no content with the input prompt; it may not be "
            "answering the question asked"
        )
    return None


def _v_ascii_letters_only(c: Constraint, text: str, tc: TestCaseCriteria) -> str | None:
    """Detects non-Latin scripts. This does not identify a language: a French
    sentence is still all-ASCII and will pass, which is the intended behaviour."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return None
    ascii_ratio = sum(1 for ch in letters if ord(ch) < 128) / len(letters)
    if ascii_ratio < ENGLISH_ASCII_THRESHOLD:
        return (
            "Response contains non-Latin script characters "
            f"({round((1 - ascii_ratio) * 100)}% of letters are outside ASCII)"
        )
    return None


def _v_non_empty(c: Constraint, text: str, tc: TestCaseCriteria) -> str | None:
    if not text or not text.strip():
        return "Response is empty"
    return None


def _v_no_shouting(c: Constraint, text: str, tc: TestCaseCriteria) -> str | None:
    words = [w for w in text.split() if w.isalpha() and len(w) > 2]
    if not words:
        return None
    shouting = sum(1 for w in words if w.isupper())
    if shouting / len(words) > SHOUT_THRESHOLD:
        return "Response is mostly written in capitals"
    return None


VALIDATORS: dict[ConstraintType, Validator] = {
    ConstraintType.MAX_WORDS: _v_max_words,
    ConstraintType.MIN_WORDS: _v_min_words,
    ConstraintType.MUST_INCLUDE: _v_must_include,
    ConstraintType.MUST_EXCLUDE: _v_must_exclude,
    ConstraintType.MUST_ANSWER_PROMPT: _v_must_answer_prompt,
    ConstraintType.ASCII_LETTERS_ONLY: _v_ascii_letters_only,
    ConstraintType.NON_EMPTY: _v_non_empty,
    ConstraintType.NO_SHOUTING: _v_no_shouting,
}

DEFAULT_REMEDIATION = "Adjust the agent response so it satisfies this instruction constraint."


def evaluate_single(criteria: TestCaseCriteria, response: str) -> DimensionResult:
    constraints = criteria.constraints
    findings: list[Finding] = []

    for constraint in constraints:
        validator = VALIDATORS[constraint.type]
        violation = validator(constraint, response, criteria)
        if violation is None:
            continue
        findings.append(
            Finding(
                rule_id=f"CMP_{constraint.type.value.upper()}",
                dimension=Dimension.COMPLIANCE,
                severity=constraint.severity,
                verification=Verification.VERIFIED,
                message=constraint.message or violation,
                evidence=truncate(response),
                remediation=DEFAULT_REMEDIATION,
            )
        )

    if constraints:
        score = max(0, 100 - VIOLATION_PENALTY * len(findings))
    else:
        score = 100

    threshold = criteria.threshold_for(Dimension.COMPLIANCE)
    passed = score >= threshold
    if not passed and not findings:
        findings.append(
            Finding(
                rule_id="CMP_BELOW_THRESHOLD",
                dimension=Dimension.COMPLIANCE,
                severity=Severity.MEDIUM,
                verification=Verification.VERIFIED,
                message=f"Compliance score {score} is below the configured threshold {threshold}.",
                evidence=truncate(response),
                remediation=DEFAULT_REMEDIATION,
            )
        )

    return DimensionResult(
        dimension=Dimension.COMPLIANCE,
        score=score,
        passed=passed,
        severity=_worst(findings),
        findings=findings,
        methodology=METHODOLOGY,
        details={
            "constraints_evaluated": len(constraints),
            "violations": len(findings),
            "constraint_types": sorted({c.type.value for c in constraints}),
            "threshold": threshold,
        },
        forced_fail=False,
    )


def _worst(findings: list[Finding]) -> Severity:
    if not findings:
        return Severity.NONE
    order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    return next(s for s in order if any(f.severity == s for f in findings))