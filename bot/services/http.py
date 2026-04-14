from __future__ import annotations

import httpx


def build_async_client() -> httpx.AsyncClient:
    """Create the shared asynchronous HTTP client used by external integrations.

    ## Parameters
        - None.

    ## Returns
        A shared AsyncClient configured for external integrations.
    """

    return httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0))
