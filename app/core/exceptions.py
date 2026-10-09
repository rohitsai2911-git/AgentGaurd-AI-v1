from typing import Any


class AppError(Exception):
    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409


class AppValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422


class EvaluationError(AppError):
    code = "EVALUATION_ERROR"
    status_code = 500


class TestCaseNotFoundError(NotFoundError):
    code = "TEST_CASE_NOT_FOUND"


class TestCaseConflictError(ConflictError):
    code = "TEST_CASE_CONFLICT"


class TestCaseHasRunsError(ConflictError):
    code = "TEST_CASE_HAS_RUNS"


class RunNotFoundError(NotFoundError):
    code = "RUN_NOT_FOUND"


class SuiteNotFoundError(NotFoundError):
    code = "SUITE_NOT_FOUND"


class SuiteConflictError(ConflictError):
    code = "SUITE_CONFLICT"


class SuiteEmptyError(ConflictError):
    code = "SUITE_EMPTY"


class SuiteExecutionNotFoundError(NotFoundError):
    code = "SUITE_EXECUTION_NOT_FOUND"


class AuthenticationError(AppError):
    code = "UNAUTHENTICATED"
    status_code = 401


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"


class EmailTakenError(ConflictError):
    code = "EMAIL_TAKEN"