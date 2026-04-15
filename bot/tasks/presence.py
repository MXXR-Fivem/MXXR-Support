from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks

if TYPE_CHECKING:
    from bot.app import BotContainer, ShopBot
    from bot.models.domain import TebexMetrics

logger = logging.getLogger(__name__)


class PresenceTask:
    def __init__(self, bot: ShopBot, container: BotContainer) -> None:
        self.bot = bot
        self.container = container
        self._show_discord_members = True
        self._cached_tebex_metrics: TebexMetrics | None = None
        self.runner.change_interval(seconds=container.config.presence.switch_interval_seconds)

    def start(self) -> None:
        """Start the Tebex-powered presence refresh loop when enabled.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        if self.container.config.presence.enabled and not self.runner.is_running():
            self.runner.start()

    def stop(self) -> None:
        """Stop the Tebex-powered presence refresh loop.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        self.runner.cancel()

    @tasks.loop(seconds=10)
    async def runner(self) -> None:
        try:
            text = await self._build_presence_text()
            if text is None:
                return
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))
            self._show_discord_members = not self._show_discord_members
        except Exception:
            logger.exception("Presence refresh failed")

    @runner.before_loop
    async def before_runner(self) -> None:
        await self.bot.wait_until_ready()

    async def _build_presence_text(self) -> str | None:
        if self._show_discord_members or self.container.tebex.client is None:
            return f"{self._get_member_count()} membres Discord"

        metrics = await self._get_tebex_metrics()
        if metrics is None:
            return f"{self._get_member_count()} membres Discord"
        return self.container.config.presence.template.format(
            sales=metrics.total_sales,
            customers=metrics.unique_customers,
        )

    async def _get_tebex_metrics(self) -> TebexMetrics | None:
        refresh_interval = timedelta(minutes=self.container.config.presence.refresh_interval_minutes)
        if self._cached_tebex_metrics is not None:
            age = discord.utils.utcnow() - self._cached_tebex_metrics.refreshed_at
            if age <= refresh_interval:
                return self._cached_tebex_metrics

        self._cached_tebex_metrics = await self.container.tebex.get_metrics()
        return self._cached_tebex_metrics

    def _get_member_count(self) -> int:
        member_count = sum(guild.member_count or 0 for guild in self.bot.guilds)
        if member_count > 0:
            return member_count
        return len(self.bot.users)
