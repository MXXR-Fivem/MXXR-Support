from __future__ import annotations
from datetime import datetime
from typing import Any

import httpx

from bot.models.domain import TebexPaymentRecord


class TebexClient:
    def __init__(self, base_url: str, api_key: str, http_client: httpx.AsyncClient) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.http_client = http_client

    async def fetch_payments_page(self, page: int = 1) -> dict[str, Any]:
        """Fetch a single paginated Tebex payments page from the plugin API.

        ## Parameters
            - page: Paginated Tebex page number to retrieve from the plugin API.

        ## Returns
            The decoded JSON payload for the requested page.
        """

        response = await self.http_client.get(
            f"{self.base_url}/payments",
            params={"paged": page},
            headers={"X-Tebex-Secret": self.api_key},
        )
        response.raise_for_status()
        return response.json()

    async def fetch_all_payments(self) -> list[TebexPaymentRecord]:
        """Fetch and normalize every Tebex payment across all available pages.

        ## Parameters
            - None.

        ## Returns
            A complete list of payments gathered across every paginated Tebex page.
        """

        payments: list[TebexPaymentRecord] = []
        next_url: str | None = f"{self.base_url}/payments?paged=1"
        page_number = 1

        while next_url:
            response = await self.http_client.get(
                next_url,
                headers={"X-Tebex-Secret": self.api_key},
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                raw_items = payload
                next_url = None
            else:
                raw_items = payload.get("data", [])
                next_url = payload.get("next_page_url")

            payments.extend(self._normalize_payment(item) for item in raw_items)
            page_number += 1

        return payments

    def _normalize_payment(self, payload: dict[str, Any]) -> TebexPaymentRecord:
        player = payload.get("player") or {}
        return TebexPaymentRecord(
            id=int(payload["id"]),
            status=str(payload.get("status", "unknown")),
            email=payload.get("email"),
            amount=payload.get("amount"),
            date=datetime.fromisoformat(payload["date"].replace("Z", "+00:00")),
            player_id=player.get("id"),
            player_name=player.get("name"),
            player_uuid=player.get("uuid"),
            raw=payload,
        )
