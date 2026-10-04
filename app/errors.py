"""Normalized error types for the connector.

Every error surfaced to the agent uses one of the codes below so
the agent can react programmatically without parsing free-text messages.
"""

from __future__ import annotations


class ConnectorError(Exception):
    """Base error returned to the agent with a machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retry_after: int | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)

    def to_dict(self) -> dict:
        d: dict = {"code": self.code, "message": self.message}
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return {"error": d}


# -- Concrete codes -----------------------------------------------------------

AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
NOT_FOUND = "NOT_FOUND"
VALIDATION_ERROR = "VALIDATION_ERROR"
RATE_LIMITED = "RATE_LIMITED"
UPSTREAM_ERROR = "UPSTREAM_ERROR"
TIMEOUT = "TIMEOUT"
CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

# Map HTTP status → error code.  Only codes we *don't* retry on.
_STATUS_MAP: dict[int, str] = {
    401: AUTHENTICATION_ERROR,
    403: AUTHORIZATION_ERROR,
    404: NOT_FOUND,
    422: VALIDATION_ERROR,
}


def error_code_for_status(status: int) -> str:
    """Return the canonical error code for an HTTP status."""
    if status in _STATUS_MAP:
        return _STATUS_MAP[status]
    if status == 429:
        return RATE_LIMITED
    if status >= 500:
        return UPSTREAM_ERROR
    # Catch-all for other 4xx
    return VALIDATION_ERROR
