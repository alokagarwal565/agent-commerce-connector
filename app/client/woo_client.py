"""WooCommerce REST API v3 HTTP client.

This is the *only* module that knows WooCommerce HTTP details.  The rest of
the application talks to ``WooCommerceClient.get()`` and receives parsed data
plus pagination metadata.

Retry/rate-limit strategy
-------------------------
* **429** – honour ``Retry-After`` header (default 10 s), up to ``max_retries``.
* **5xx** – exponential back-off (1 s, 2 s, 4 s …), up to ``max_retries``.
* **4xx** (except 429) – never retried; raised immediately.
* **Timeout** – raised immediately (no retry).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

from app.config import Settings
from app.errors import (
    RATE_LIMITED,
    TIMEOUT,
    UPSTREAM_ERROR,
    ConnectorError,
    error_code_for_status,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WooResponse:
    """Parsed WooCommerce response with optional pagination metadata."""

    data: dict | list
    total: int | None = None
    total_pages: int | None = None


class WooCommerceClient:
    """Thin async wrapper around the WooCommerce REST API v3."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = f"{settings.woocommerce_store_url}/wp-json/wc/v3"
        self._auth = (
            settings.woocommerce_consumer_key.get_secret_value(),
            settings.woocommerce_consumer_secret.get_secret_value(),
        )
        self._max_retries = settings.max_retries
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout_seconds),
        )

    # -- public API -----------------------------------------------------------

    async def get(
        self,
        endpoint: str,
        params: dict | None = None,
    ) -> WooResponse:
        """GET ``/wp-json/wc/v3/{endpoint}`` with retry/rate-limit handling."""
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        attempt = 0

        while True:
            try:
                resp = await self._client.get(
                    url,
                    params=params,
                    auth=self._auth,
                )
            except httpx.TimeoutException as exc:
                raise ConnectorError(TIMEOUT, f"Request timed out: {url}") from exc
            except httpx.HTTPError as exc:
                raise ConnectorError(
                    UPSTREAM_ERROR,
                    f"HTTP transport error: {exc}",
                ) from exc

            if resp.status_code == 429:
                attempt += 1
                if attempt > self._max_retries:
                    retry_after = _retry_after(resp)
                    raise ConnectorError(
                        RATE_LIMITED,
                        f"WooCommerce rate limit reached. Retry after {retry_after}s.",
                        retry_after=retry_after,
                    )
                wait = _retry_after(resp)
                logger.warning(
                    "rate_limited attempt=%d wait=%ds endpoint=%s",
                    attempt,
                    wait,
                    endpoint,
                )
                await asyncio.sleep(wait)
                continue

            if resp.status_code >= 500:
                attempt += 1
                if attempt > self._max_retries:
                    raise ConnectorError(
                        UPSTREAM_ERROR,
                        f"WooCommerce server error ({resp.status_code}) after {attempt} attempts.",
                    )
                wait = min(2 ** (attempt - 1), 16)  # 1, 2, 4 … capped at 16 s
                logger.warning(
                    "server_error status=%d attempt=%d wait=%ds endpoint=%s",
                    resp.status_code,
                    attempt,
                    wait,
                    endpoint,
                )
                await asyncio.sleep(wait)
                continue

            if resp.status_code >= 400:
                code = error_code_for_status(resp.status_code)
                # Try to pull a message from the WooCommerce error body
                detail = _extract_detail(resp)
                raise ConnectorError(code, detail)

            # Success
            return WooResponse(
                data=resp.json(),
                total=_int_header(resp, "X-WP-Total"),
                total_pages=_int_header(resp, "X-WP-TotalPages"),
            )

    async def close(self) -> None:
        await self._client.aclose()


# -- helpers ------------------------------------------------------------------


def _retry_after(resp: httpx.Response, default: int = 10) -> int:
    """Read ``Retry-After`` header, falling back to *default* seconds."""
    raw = resp.headers.get("Retry-After")
    if raw is not None:
        try:
            return max(int(raw), 1)
        except ValueError:
            pass
    return default


def _int_header(resp: httpx.Response, name: str) -> int | None:
    raw = resp.headers.get(name)
    if raw is not None:
        try:
            return int(raw)
        except ValueError:
            pass
    return None


def _extract_detail(resp: httpx.Response) -> str:
    """Best-effort extraction of a useful error message from WooCommerce."""
    try:
        body = resp.json()
        if isinstance(body, dict):
            return body.get("message", f"HTTP {resp.status_code}")
    except Exception:
        pass
    return f"HTTP {resp.status_code}"
