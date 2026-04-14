from __future__ import annotations

import logging
from datetime import datetime, timedelta

from bot.models.domain import TebexMetrics, TebexPaymentRecord
from bot.services.tebex_client import TebexClient
from bot.storage.database import Database
from bot.utils.time import utcnow

logger = logging.getLogger(__name__)


class TebexService:
    CACHE_KEY = "tebex_metrics_v2"
    COMPLETED_STATUSES = {
        "complete",
        "completed",
        "paid",
        "success",
    }

    def __init__(
        self,
        client: TebexClient | None,
        database: Database,
        cache_ttl: timedelta = timedelta(minutes=15),
    ) -> None:
        self.client = client
        self.database = database
        self.cache_ttl = cache_ttl

    async def get_metrics(self, force_refresh: bool = False) -> TebexMetrics:
        """Return Tebex sales metrics, using the cache unless a refresh is required.

        ## Parameters
            - force_refresh: When True, bypasses the cache and refreshes from Tebex.

        ## Returns
            Tebex sales and unique customer metrics.
        """

        if self.client is None:
            raise RuntimeError("Tebex is not configured.")

        cached = await self.database.get_cache_entry(self.CACHE_KEY)
        if not force_refresh and cached is not None:
            updated_at = datetime.fromisoformat(cached["updated_at"])
            if utcnow() - updated_at <= self.cache_ttl:
                payload = cached["payload"]
                return TebexMetrics(
                    total_sales=int(payload["total_sales"]),
                    unique_customers=int(payload["unique_customers"]),
                    refreshed_at=updated_at,
                )

        payments = await self.client.fetch_all_payments()
        completed_payments = self._get_completed_payments(payments)
        unique_customers = {
            self._customer_key(payment)
            for payment in completed_payments
            if self._customer_key(payment) is not None
        }

        metrics = TebexMetrics(
            total_sales=len(completed_payments),
            unique_customers=len(unique_customers),
            refreshed_at=utcnow(),
        )
        await self.database.set_cache_entry(
            key=self.CACHE_KEY,
            payload={
                "total_sales": metrics.total_sales,
                "unique_customers": metrics.unique_customers,
            },
            updated_at=metrics.refreshed_at,
        )
        logger.info(
            "Refreshed Tebex metrics: sales=%s customers=%s",
            metrics.total_sales,
            metrics.unique_customers,
        )
        return metrics

    def _get_completed_payments(self, payments: list[TebexPaymentRecord]) -> list[TebexPaymentRecord]:
        seen_ids: set[int] = set()
        completed: list[TebexPaymentRecord] = []
        for payment in payments:
            if payment.id in seen_ids:
                continue
            seen_ids.add(payment.id)
            if self._is_completed_payment(payment):
                completed.append(payment)
        return completed

    def _is_completed_payment(self, payment: TebexPaymentRecord) -> bool:
        status = payment.status.strip().lower()
        return status in self.COMPLETED_STATUSES

    def _customer_key(self, payment: TebexPaymentRecord) -> str | None:
        if payment.player_uuid:
            return f"uuid:{payment.player_uuid.strip().lower()}"
        if payment.player_id:
            return f"id:{payment.player_id}"
        if payment.email:
            return f"email:{payment.email.strip().lower()}"
        if payment.player_name:
            return f"name:{payment.player_name.strip().lower()}"

        raw_player = payment.raw.get("player") or {}
        if isinstance(raw_player, dict):
            for field in ("uuid", "id", "email", "name", "username", "ign"):
                value = raw_player.get(field)
                if value is None:
                    continue
                normalized = str(value).strip().lower()
                if normalized:
                    return f"player_{field}:{normalized}"

        for field in ("username", "name", "ign", "customer_name"):
            value = payment.raw.get(field)
            if value is None:
                continue
            normalized = str(value).strip().lower()
            if normalized:
                return f"raw_{field}:{normalized}"
        return None
