from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks

from bot.utils.time import utcnow

if TYPE_CHECKING:
    from bot.app import BotContainer, ShopBot

logger = logging.getLogger(__name__)


class PollWatcherTask:
    def __init__(self, bot: ShopBot, container: BotContainer) -> None:
        self.bot = bot
        self.container = container
        self.runner.change_interval(seconds=30)

    def start(self) -> None:
        if not self.runner.is_running():
            self.runner.start()

    def stop(self) -> None:
        self.runner.cancel()

    @tasks.loop(seconds=30)
    async def runner(self) -> None:
        due_polls = await self.container.database.get_active_polls_due(utcnow())
        for poll in due_polls:
            try:
                results = await self.container.polls.finalize_poll(poll)
                channel = self.bot.get_channel(poll.channel_id)
                if not isinstance(channel, discord.TextChannel):
                    continue
                if poll.message_id is not None:
                    try:
                        message = await channel.fetch_message(poll.message_id)
                        await message.edit(embed=self.container.polls.build_results_embed(poll, results), view=None)
                    except discord.NotFound:
                        pass

                winner_announcement = self.container.polls.build_winner_announcement(poll, results)
                await channel.send(content=winner_announcement, embed=self.container.polls.build_results_embed(poll, results))
            except Exception:
                logger.exception("Failed to end poll %s", poll.id)

    @runner.before_loop
    async def before_runner(self) -> None:
        await self.bot.wait_until_ready()
