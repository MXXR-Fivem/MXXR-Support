from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import tasks

from bot.views.giveaway_views import GiveawayJoinView
from bot.utils.time import utcnow

if TYPE_CHECKING:
    from bot.app import BotContainer, ShopBot

logger = logging.getLogger(__name__)


class GiveawayWatcherTask:
    def __init__(self, bot: ShopBot, container: BotContainer) -> None:
        self.bot = bot
        self.container = container
        self.runner.change_interval(seconds=container.config.giveaways.check_interval_seconds)

    def start(self) -> None:
        """Start the periodic giveaway watcher if it is not already running.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        if not self.runner.is_running():
            self.runner.start()

    def stop(self) -> None:
        """Stop the periodic giveaway watcher.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        self.runner.cancel()

    @tasks.loop(seconds=30)
    async def runner(self) -> None:
        due_giveaways = await self.container.database.get_active_giveaways_due(utcnow())
        for giveaway in due_giveaways:
            try:
                winners = await self.container.giveaways.finalize_giveaway(giveaway)
                participant_count = await self.container.database.count_giveaway_entries(int(giveaway.id))
                channel = self.bot.get_channel(giveaway.channel_id)
                if not isinstance(channel, discord.TextChannel):
                    continue
                if giveaway.message_id is not None:
                    try:
                        message = await channel.fetch_message(giveaway.message_id)
                        await message.edit(
                            embed=self.container.giveaways.build_results_embed(
                                giveaway,
                                winners,
                                participant_count=participant_count,
                            ),
                            view=None,
                        )
                    except discord.NotFound:
                        pass
                if winners:
                    winners_mentions = " ".join(f"<@{winner}>" for winner in winners)
                    await channel.send(
                        content=f"🎉 Félicitations {winners_mentions}",
                        embed=self.container.giveaways.build_results_embed(
                            giveaway,
                            winners,
                            participant_count=participant_count,
                        ),
                    )
                else:
                    await channel.send(
                        embed=self.container.giveaways.build_results_embed(
                            giveaway,
                            winners,
                            participant_count=participant_count,
                        )
                    )
            except Exception:
                logger.exception("Failed to end giveaway %s", giveaway.id)

    @runner.before_loop
    async def before_runner(self) -> None:
        await self.bot.wait_until_ready()
