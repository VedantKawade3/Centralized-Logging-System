"""HTTP client wrappers that automatically forward correlation headers."""

from __future__ import annotations

from typing import Any

import httpx

from app.integration.correlation_headers import inject_correlation_headers


def create_async_client(
    *,
    base_url: str | None = None,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """Create an AsyncClient with context-aware default headers."""
    return httpx.AsyncClient(
        base_url=base_url or "",
        timeout=timeout,
        headers=inject_correlation_headers(headers),
        **kwargs,
    )


async def request_with_context(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """Send a request while forwarding request/trace/session IDs."""
    merged_headers = inject_correlation_headers(headers)
    return await client.request(method=method, url=url, headers=merged_headers, **kwargs)

