from app.evaluation.modules.compliance import VALIDATORS, evaluate_single
from app.evaluation.types import ConstraintType, Severity
from tests.factories import REFUND_ANSWER, REFUND_PROMPT, make_criteria, make_constraint

LONG = " ".join(["word"] * 200)


def test_no_constraints_scores_one_hundred():
    result = evaluate_single(make_criteria(), REFUND_ANSWER)

    assert result.score == 100
    assert result.passed is True
    assert result.details["constraints_evaluated"] == 0


def test_max_words_violation_is_detected():
    criteria = make_criteria(
        constraints=[make_constraint(ConstraintType.MAX_WORDS, value=10)]
    )
    result = evaluate_single(criteria, "one two three four five six seven eight nine ten eleven")

    assert result.score == 75
    assert any(f.rule_id == "CMP_MAX_WORDS" for f in result.findings)


def test_min_words_violation_is_detected():
    criteria = make_criteria(constraints=[make_constraint(ConstraintType.MIN_WORDS, value=20)])
    result = evaluate_single(criteria, "too short")

    assert any(f.rule_id == "CMP_MIN_WORDS" for f in result.findings)


def test_must_include_violation_lists_missing_phrases():
    criteria = make_criteria(
        constraints=[
            make_constraint(ConstraintType.MUST_INCLUDE, phrases=["store credit", "returns"])
        ]
    )
    result = evaluate_single(criteria, "You may request store credit later.")

    finding = next(f for f in result.findings if f.rule_id == "CMP_MUST_INCLUDE")
    assert "returns" in finding.message
    assert "store credit" not in finding.message


def test_must_exclude_violation_is_detected():
    criteria = make_criteria(
        constraints=[make_constraint(ConstraintType.MUST_EXCLUDE, phrases=["guaranteed"])]
    )
    result = evaluate_single(criteria, "This is guaranteed to work.")

    assert any(f.rule_id == "CMP_MUST_EXCLUDE" for f in result.findings)


def test_must_answer_prompt_flags_unrelated_response():
    criteria = make_criteria(
        constraints=[make_constraint(ConstraintType.MUST_ANSWER_PROMPT, severity=Severity.HIGH)]
    )
    result = evaluate_single(criteria, "Bananas are an excellent fruit.")

    assert any(f.rule_id == "CMP_MUST_ANSWER_PROMPT" for f in result.findings)


def test_must_answer_prompt_passes_a_relevant_response():
    criteria = make_criteria(
        constraints=[make_constraint(ConstraintType.MUST_ANSWER_PROMPT)]
    )
    result = evaluate_single(criteria, REFUND_ANSWER)

    assert result.score == 100


def test_non_empty_violation_on_blank_response():
    criteria = make_criteria(constraints=[make_constraint(ConstraintType.NON_EMPTY)])
    result = evaluate_single(criteria, "   ")

    assert any(f.rule_id == "CMP_NON_EMPTY" for f in result.findings)


def test_ascii_letters_only_flags_non_latin_scripts():
    criteria = make_criteria(
        constraints=[make_constraint(ConstraintType.ASCII_LETTERS_ONLY)]
    )
    result = evaluate_single(criteria, "\u0930\u093f\u092b\u0902\u0921 \u0905\u0935\u0947\u091f\u094d \u091f\u094d\u092f\u094b\u092a \u0926\u0947\u0928\u0947")

    assert any(f.rule_id == "CMP_ASCII_LETTERS_ONLY" for f in result.findings)


def test_ascii_letters_only_does_not_claim_language_detection():
    """The check is script-based only; a Latin-script foreign sentence passes."""
    criteria = make_criteria(
        constraints=[make_constraint(ConstraintType.ASCII_LETTERS_ONLY)]
    )
    result = evaluate_single(criteria, "Le remboursement est disponible sous trente jours.")

    assert result.score == 100


def test_no_shouting_flags_capitals():
    criteria = make_criteria(
        constraints=[make_constraint(ConstraintType.NO_SHOUTING)]
    )
    result = evaluate_single(criteria, "YOUR REFUND IS APPROVED RIGHT NOW TODAY")

    assert any(f.rule_id == "CMP_NO_ALL_CAPS_SHOUTING" for f in result.findings)


def test_custom_severity_is_respected():
    criteria = make_criteria(
        constraints=[
            make_constraint(
                ConstraintType.MUST_EXCLUDE, phrases=["secret"], severity=Severity.CRITICAL
            )
        ]
    )
    result = evaluate_single(criteria, "The secret is out.")

    finding = next(f for f in result.findings if f.rule_id == "CMP_MUST_EXCLUDE")
    assert finding.severity == Severity.CRITICAL


def test_every_constraint_type_has_a_validator():
    assert set(VALIDATORS) == set(ConstraintType)


def test_score_subtracts_a_fixed_penalty_per_violation():
    criteria = make_criteria(
        constraints=[
            make_constraint(ConstraintType.MUST_INCLUDE, phrases=["alpha"]),
            make_constraint(ConstraintType.MUST_INCLUDE, phrases=["beta"]),
        ]
    )
    result = evaluate_single(criteria, "Neither term appears here.")

    assert result.details["violations"] == 2
    assert result.score == 50


def test_prompt_is_available_to_compliance_module():
    assert REFUND_PROMPT