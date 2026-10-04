"""Shared response wrappers."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list with optional WooCommerce total metadata."""

    data: list[T]
    page: int
    per_page: int
    total: int | None = None
    total_pages: int | None = None


class ErrorResponse(BaseModel):
    """Agent-facing error envelope."""

    code: str
    message: str
    retry_after: int | None = None
