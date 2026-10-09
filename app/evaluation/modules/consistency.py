from __future__ import annotations

import itertools

from app.evaluation.normalize import (
    extract_all_labeled_values,
    extract_labeled_values,
    normalize_text,
    overlap,
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

METHODOLOGY_CROSS = (
    "Cross-response mode. Agreement score = mean pairwise overlap coefficient across "
    "all response pairs. A label carrying different values in different responses is "
    "a verified contradiction and caps the score at 40."
)

METHODOLOGY_INTERNAL = (
    "Internal mode (single response). Detects the same label carrying two different "
    "values within one response, and polarity flips where the same subject appears "
    "with opposing markers (always/never, can/cannot, is/is not)."
)

MODE_CROSS = "cross_response"
MODE_INTERNAL = "internal"

CONTRADICTION_CAP = 40
SELF_CONTRADICTION_PENALTY = 25
POLARITY_FLIP_PENALTY = 15
MIN_AGREEMENT_SUBJECT_TOKENS = 2

POLARITY_PAIRS = [
    ({"always"}, {"never"}),
    ({"can"}, {"cannot", "cant", "can not"}),
    ({"is"}, {"is not"}),
    ({"will"}, {"will not", "wont", "won t"}),
    ({"includes"}, {"excludes"}),
    ({"enabled"}, {"disabled"}),
]


def mode_for(response_count: int) -> str:
    return MODE_CROSS if response_count >= 2 else MODE_INTERNAL


def evaluate(criteria: TestCaseCriteria, responses: list[str]) -> DimensionResult:
    if mode_for(len(responses)) == MODE_CROSS:
        return _evaluate_cross(criteria, responses)
    return _evaluate_internal(criteria, responses[0] if responses else "")


def _evaluate_cross(criteria: TestCaseCriteria, responses: list[str]) -> DimensionResult:
    findings: list[Finding] = []
    forced_fail = False

    token_sets = [token_set(r) for r in responses]
    pairs = list(itertools.combinations(range(len(responses)), 2))
    if pairs:
        agreements = [overlap(token_sets[i], token_sets[j]) for i, j in pairs]
        agreement = sum(agreements) / len(agreements)
    else:
        agreement = 0.0

    value_maps = [extract_labeled_values(r) for r in responses]
    labels: list[str] = []
    for value_map in value_maps:
        for label in value_map:
            if label not in labels:
                labels.append(label)

    contradictions = 0
    for label in labels:
        seen = [(i, m[label]) for i, m in enumerate(value_maps) if label in m]
        values = {round(v, 6) for _, v in seen}
        if len(values) > 1:
            forced_fail = True
            contradictions += 1
            rendered = ", ".join(f"response {i} said {_fmt(v)}" for i, v in seen)
            findings.append(
                Finding(
                    rule_id="CON_CROSS_RESPONSE_CONTRADICTION",
                    dimension=Dimension.CONSISTENCY,
                    severity=Severity.HIGH,
                    verification=Verification.VERIFIED,
                    message=f"Responses disagree on '{label}': {rendered}.",
                    evidence=truncate(
                        "; ".join(f"[{i}] {truncate(responses[i], 80)}" for i, _ in seen)
                    ),
                    remediation=(
                        "Pin the agent to a single source of truth for this value so "
                        "repeat sampling returns the same figure."
                    ),
                )
            )

    score = clamp(agreement * 100)
    if contradictions:
        score = min(score, CONTRADICTION_CAP)

    threshold = criteria.threshold_for(Dimension.CONSISTENCY)
    passed = score >= threshold and not forced_fail
    if not passed and not findings:
        findings.append(
            Finding(
                rule_id="CON_LOW_AGREEMENT",
                dimension=Dimension.CONSISTENCY,
                severity=Severity.MEDIUM,
                verification=Verification.RISK,
                message=(
                    f"Mean pairwise agreement {round(agreement * 100)}% is below the "
                    f"configured threshold {threshold}%."
                ),
                evidence=truncate(" || ".join(responses), 240),
                remediation="Reduce sampling variance by grounding responses in one source of truth.",
            )
        )

    return DimensionResult(
        dimension=Dimension.CONSISTENCY,
        score=score,
        passed=passed,
        severity=_worst(findings),
        findings=findings,
        methodology=METHODOLOGY_CROSS,
        details={
            "mode": MODE_CROSS,
            "responses_compared": len(responses),
            "pairs_compared": len(pairs),
            "agreement": round(agreement, 4),
            "contradiction_count": contradictions,
            "labels_compared": len(labels),
            "threshold": threshold,
        },
        forced_fail=forced_fail,
    )


def _evaluate_internal(criteria: TestCaseCriteria, response: str) -> DimensionResult:
    findings: list[Finding] = []
    forced_fail = False
    self_contradictions = 0
    polarity_flips = 0

    by_label: dict[str, list[float]] = {}
    for label, value in extract_all_labeled_values(response):
        by_label.setdefault(label, []).append(value)

    for label, values in by_label.items():
        distinct = {round(v, 6) for v in values}
        if len(distinct) > 1:
            forced_fail = True
            self_contradictions += 1
            rendered = " and ".join(_fmt(v) for v in dict.fromkeys(values))
            findings.append(
                Finding(
                    rule_id="CON_SELF_CONTRADICTION",
                    dimension=Dimension.CONSISTENCY,
                    severity=Severity.HIGH,
                    verification=Verification.VERIFIED,
                    message=(
                        f"Response gives conflicting values for '{label}': {rendered}."
                    ),
                    evidence=truncate(response),
                    remediation=(
                        "Resolve the conflict before responding. A self-contradicting "
                        "answer is worse than an incomplete one."
                    ),
                )
            )

    sentences = [s for s in normalize_text(response).split(".") if s.strip()]
    for sentence in sentences:
        words = set(sentence.split())
        for positive, negative in POLARITY_PAIRS:
            if not (words & positive) or not (words & negative):
                continue
            subject_a = _subject(words, positive)
            subject_b = _subject(words, negative)
            if not subject_a or not subject_b:
                continue
            if overlap(subject_a, subject_b) < 0.34:
                continue
            polarity_flips += 1
            findings.append(
                Finding(
                    rule_id="CON_POLARITY_FLIP",
                    dimension=Dimension.CONSISTENCY,
                    severity=Severity.MEDIUM,
                    verification=Verification.RISK,
                    message=(
                        "Opposing claims about the same subject in one response: "
                        + truncate(sentence, 120)
                    ),
                    evidence=truncate(response),
                    remediation=(
                        "State one position per subject. Contradictory polarity reads as "
                        "unreliable to customers."
                    ),
                )
            )
            break

    score = clamp(
        100
        - SELF_CONTRADICTION_PENALTY * self_contradictions
        - POLARITY_FLIP_PENALTY * polarity_flips
    )
    threshold = criteria.threshold_for(Dimension.CONSISTENCY)
    passed = score >= threshold and not forced_fail

    return DimensionResult(
        dimension=Dimension.CONSISTENCY,
        score=score,
        passed=passed,
        severity=_worst(findings),
        findings=findings,
        methodology=METHODOLOGY_INTERNAL,
        details={
            "mode": MODE_INTERNAL,
            "responses_compared": 1,
            "sentences_scanned": len(sentences),
            "labels_found": len(by_label),
            "self_contradiction_count": self_contradictions,
            "polarity_flip_count": polarity_flips,
            "threshold": threshold,
        },
        forced_fail=forced_fail,
    )


def _subject(words: set[str], markers: set[str]) -> set[str]:
    content = words - markers
    return content if len(content) >= MIN_AGREEMENT_SUBJECT_TOKENS else set()


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def _worst(findings: list[Finding]) -> Severity:
    if not findings:
        return Severity.NONE
    order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    return next(s for s in order if any(f.severity == s for f in findings))