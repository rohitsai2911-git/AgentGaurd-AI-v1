from __future__ import annotations

from app.evaluation.normalize import (
    DATE_RE,
    EMAIL_RE,
    ORDER_REF_RE,
    PHONE_RE,
    URL_RE,
    extract_entities,
    extract_labeled_values,
    extract_numbers,
    normalize_text,
    split_sentences,
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
    "Extracts sentences containing a claim signal (numeric literal, date, capitalised "
    "entity, or superlative), then tests each claim against the grounding source "
    "(expected_answer + referenced_facts). Unsupported numbers, identifiers and "
    "entities are reported as heuristic 'risk'. A value that contradicts a labelled "
    "value in the grounding source is reported as 'verified'."
)

VERDICT_CONTRADICTION = "contradiction_detected"
VERDICT_UNVERIFIABLE = "unverifiable_claims_detected"
VERDICT_NONE = "no_contradiction_detected"

ABSOLUTE_TERMS = {
    "always", "never", "guaranteed", "guarantees", "definitely", "certainly",
    "best", "cheapest", "fastest", "number one", "most trusted", "only", "all",
}

RISK_PENALTY = {"high": 30, "medium": 15, "low": 8}
VERIFIED_PENALTY = 45


def evaluate_single(criteria: TestCaseCriteria, response: str):
    grounding_text = criteria.grounding_text
    grounding_norm = normalize_text(grounding_text)
    grounding_numbers = set(extract_numbers(grounding_text))
    grounding_values = extract_labeled_values(grounding_text)

    findings: list[Finding] = []
    unsupported: list[str] = []
    contradicted: list[str] = []
    forced_fail = False

    for sentence in split_sentences(response):
        sentence_norm = normalize_text(sentence)
        sentence_numbers = extract_numbers(sentence)
        sentence_entities = extract_entities(sentence)
        has_absolute = bool(ABSOLUTE_TERMS & set(sentence_norm.split()))

        is_claim = bool(
            sentence_numbers or sentence_entities or has_absolute or DATE_RE.search(sentence)
        )
        if not is_claim:
            continue

        # Grounding support is judged per claim value, never by topical overlap:
        # a sentence sharing common words with the grounding source can still assert
        # a figure or entity the source never mentions.

        # Verified contradiction: the response labels a value that the grounding
        # source labels with a different value.
        for label, value in extract_labeled_values(sentence).items():
            if label in grounding_values and abs(grounding_values[label] - value) > 1e-6:
                forced_fail = True
                contradicted.append(f"{label}: response={_fmt(value)} expected={_fmt(grounding_values[label])}")
                findings.append(
                    Finding(
                        rule_id="HAL_CONTRADICTED_VALUE",
                        dimension=Dimension.HALLUCINATION,
                        severity=Severity.HIGH,
                        verification=Verification.VERIFIED,
                        message=(
                            f"Response states '{label} = {_fmt(value)}' but the grounding "
                            f"source states '{label} = {_fmt(grounding_values[label])}'."
                        ),
                        evidence=truncate(sentence),
                        remediation=(
                            "Correct the value to match the grounding source, or update the "
                            "referenced facts if the new value is correct."
                        ),
                    )
                )

        # Unverifiable identifiers: high-severity specificity absent from grounding.
        for pattern, rule_id, label in (
            (EMAIL_RE, "HAL_UNSUPPORTED_EMAIL", "email address"),
            (PHONE_RE, "HAL_UNSUPPORTED_PHONE", "phone number"),
            (URL_RE, "HAL_UNSUPPORTED_URL", "URL"),
            (ORDER_REF_RE, "HAL_UNSUPPORTED_REFERENCE_ID", "order/reference identifier"),
        ):
            for match in pattern.findall(sentence):
                snippet = match if isinstance(match, str) else match[0]
                if normalize_text(snippet) and normalize_text(snippet) in grounding_norm:
                    continue
                unsupported.append(snippet)
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        dimension=Dimension.HALLUCINATION,
                        severity=Severity.HIGH,
                        verification=Verification.RISK,
                        message=(
                            f"Response contains a specific {label} that does not appear in "
                            f"the grounding source: {truncate(snippet, 60)}"
                        ),
                        evidence=truncate(sentence),
                        remediation=(
                            "Remove the invented identifier or ground it in a real record. "
                            "Fabricated identifiers are the strongest hallucination signal "
                            "in a support agent."
                        ),
                    )
                )

        for number in sentence_numbers:
            if any(abs(number - g) <= 1e-6 for g in grounding_numbers):
                continue
            unsupported.append(str(_fmt(number)))
            findings.append(
                Finding(
                    rule_id="HAL_UNSUPPORTED_NUMBER",
                    dimension=Dimension.HALLUCINATION,
                    severity=Severity.MEDIUM,
                    verification=Verification.RISK,
                    message=(
                        f"Number {_fmt(number)} is not supported by the grounding source."
                    ),
                    evidence=truncate(sentence),
                    remediation=(
                        "Confirm the figure against the authoritative record before stating it, "
                        "or omit it."
                    ),
                )
            )

        for entity in sentence_entities:
            if entity.lower() in grounding_norm:
                continue
            unsupported.append(entity)
            findings.append(
                Finding(
                    rule_id="HAL_UNSUPPORTED_ENTITY",
                    dimension=Dimension.HALLUCINATION,
                    severity=Severity.MEDIUM,
                    verification=Verification.RISK,
                    message=f"Entity '{entity}' is not mentioned in the grounding source.",
                    evidence=truncate(sentence),
                    remediation=(
                        "Introduce the entity only if the grounding source supports it, "
                        "otherwise remove the reference."
                    ),
                )
            )

        if has_absolute and not _absolute_is_grounded(sentence_norm, grounding_norm):
            unsupported.append(sentence)
            findings.append(
                Finding(
                    rule_id="HAL_UNSUPPORTED_ABSOLUTE_CLAIM",
                    dimension=Dimension.HALLUCINATION,
                    severity=Severity.MEDIUM,
                    verification=Verification.RISK,
                    message=(
                        "Absolute or superlative claim with no grounding support: "
                        + truncate(sentence, 120)
                    ),
                    evidence=truncate(sentence),
                    remediation="Soften absolute claims into qualified, verifiable statements.",
                )
            )

    penalty = 100 - sum(
        (VERIFIED_PENALTY if f.verification == Verification.VERIFIED else RISK_PENALTY[f.severity.value])
        for f in findings
    )
    score = clamp(penalty)

    threshold = criteria.threshold_for(Dimension.HALLUCINATION)
    passed = score >= threshold and not forced_fail
    if not passed and not findings:
        findings.append(
            Finding(
                rule_id="HAL_BELOW_THRESHOLD",
                dimension=Dimension.HALLUCINATION,
                severity=Severity.MEDIUM,
                verification=Verification.RISK,
                message=f"Hallucination risk score {score} is below the threshold {threshold}.",
                evidence=truncate(response),
                remediation="Re-check the response against the grounding source.",
            )
        )

    if contradicted:
        verdict = VERDICT_CONTRADICTION
    elif unsupported:
        verdict = VERDICT_UNVERIFIABLE
    else:
        verdict = VERDICT_NONE

    return DimensionResult(
        dimension=Dimension.HALLUCINATION,
        score=score,
        passed=passed,
        severity=_worst(findings),
        findings=findings,
        methodology=METHODOLOGY,
        details={
            "verdict": verdict,
            "unsupported_claim_count": len(unsupported),
            "contradicted_value_count": len(contradicted),
            "risk_finding_count": sum(1 for f in findings if f.verification == Verification.RISK),
            "verified_finding_count": sum(
                1 for f in findings if f.verification == Verification.VERIFIED
            ),
            "threshold": threshold,
        },
        forced_fail=forced_fail,
    )


def _absolute_is_grounded(sentence_norm: str, grounding_norm: str) -> bool:
    """An absolute claim counts as grounded only if the grounding source uses the
    same absolute term itself. Weaker grounds are not treated as support."""
    return bool(ABSOLUTE_TERMS & (set(sentence_norm.split()) & set(grounding_norm.split())))


def _is_identifiable(sentence: str) -> bool:
    """True when the sentence is a factual reference rather than an aside."""
    return any(p.search(sentence) for p in (EMAIL_RE, PHONE_RE, URL_RE, ORDER_REF_RE, DATE_RE))


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else str(n)


def _worst(findings: list[Finding]) -> Severity:
    if not findings:
        return Severity.NONE
    order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    return next(s for s in order if any(f.severity == s for f in findings))