from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks

if TYPE_CHECKING:
    from bot.app import BotContainer, ShopBot

logger = logging.getLogger(__name__)


class PresenceTask:
    def __init__(self, bot: ShopBot, container: BotContainer) -> None:
        self.bot = bot
        self.container = container
        self.runner.change_interval(minutes=container.config.presence.refresh_interval_minutes)

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

    @tasks.loop(minutes=15)
    async def runner(self) -> None:
        if self.container.tebex.client is None:
            return
        try:
            metrics = await self.container.tebex.get_metrics()
            text = self.container.config.presence.template.format(
                sales=metrics.total_sales,
                customers=metrics.unique_customers,
            )
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))
        except Exception:
            logger.exception("Presence refresh failed")

    @runner.before_loop
    async def before_runner(self) -> None:
        await self.bot.wait_until_ready()
