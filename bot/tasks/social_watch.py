from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks

if TYPE_CHECKING:
    from bot.app import BotContainer, ShopBot

logger = logging.getLogger(__name__)


class SocialWatcherTask:
    def __init__(self, bot: ShopBot, container: BotContainer) -> None:
        self.bot = bot
        self.container = container
        self.runner.change_interval(minutes=self._resolve_interval_minutes())

    def start(self) -> None:
        """Start the social announcement polling loop if it is not already running.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        if not self.runner.is_running():
            self.runner.start()

    def stop(self) -> None:
        """Stop the social announcement polling loop.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        self.runner.cancel()

    @tasks.loop(minutes=10)
    async def runner(self) -> None:
        try:
            posts = await self.container.social_announcer.collect_unpublished_posts()
            if not posts:
                return
            channel = self.bot.get_channel(self.container.config.channels.news)
            if not isinstance(channel, discord.TextChannel):
                return
            for post in posts:
                await channel.send(embed=self.container.social_announcer.build_embed(post))
                await self.container.social_announcer.mark_as_published(post)
        except Exception:
            logger.exception("Social post polling failed")

    @runner.before_loop
    async def before_runner(self) -> None:
        await self.bot.wait_until_ready()

    def _resolve_interval_minutes(self) -> int:
        intervals = []
        social = self.container.config.social
        if social.youtube.enabled:
            intervals.append(social.youtube.poll_interval_minutes)
        if social.x.enabled:
            intervals.append(social.x.poll_interval_minutes)
        if social.tiktok.enabled:
            intervals.append(social.tiktok.poll_interval_minutes)
        return min(intervals) if intervals else 15
