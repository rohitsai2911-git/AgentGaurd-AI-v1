from app.evaluation.types import Constraint, TestCaseCriteria

REFUND_PROMPT = "Can I get a refund after 45 days?"

REFUND_ANSWER = (
    "Refunds are available within 30 days of purchase. This order was placed 45 days "
    "ago so it cannot be refunded. Store credit is offered instead."
)

REFUND_GOOD_RESPONSE = (
    "Thanks for checking in. Refunds are available within 30 days of the order date. "
    "This order was placed 45 days ago, so it falls outside that window and I cannot "
    "process a refund. What I can do is offer store credit for the full order value."
)


def make_criteria(**overrides) -> TestCaseCriteria:
    payload: dict = {
        "id": "tc-unit",
        "name": "Unit test case",
        "input_prompt": REFUND_PROMPT,
        "expected_answer": REFUND_ANSWER,
        "referenced_facts": ["The refund window is 30 days."],
    }
    payload.update(overrides)
    return TestCaseCriteria(**payload)


def make_constraint(constraint_type, **kwargs) -> Constraint:
    return Constraint(type=constraint_type, **kwargs)