from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.staff.polls import build_poll_record, parse_poll_options
from bot.guards.checks import has_staff_permissions
from bot.utils.time import parse_duration_to_timedelta
from bot.views.poll_views import PollVoteView

if TYPE_CHECKING:
    from bot.app import ShopBot


class PollsCog(commands.Cog):
    def __init__(self, bot: ShopBot) -> None:
        self.bot = bot

    @app_commands.command(name="poll-create", description="Crée un sondage staff")
    async def poll_create(
        self,
        interaction: discord.Interaction,
        question: str,
        description: str,
        option_1: str,
        option_2: str,
        duration: str,
        option_3: str | None = None,
        option_4: str | None = None,
        option_5: str | None = None,
    ) -> None:
        container = self.bot.container
        assert container is not None
        self._ensure_staff(interaction)
        try:
            parsed_options = parse_poll_options(
                (option_1, option_2, option_3, option_4, option_5),
                container.config.polls.max_options,
            )
            duration_delta = parse_duration_to_timedelta(duration)
        except ValueError as error:
            await interaction.response.send_message(
                embed=container.embeds.error("Paramètres invalides", str(error)),
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        poll = build_poll_record(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            author_id=interaction.user.id,
            question=question,
            description=description,
            options=parsed_options,
            duration=duration_delta,
        )
        await container.polls.create_poll(poll)
        message = await interaction.channel.send(
            embed=container.polls.build_poll_embed(poll),
            view=PollVoteView(option_count=len(parsed_options)),
        )
        await container.database.set_poll_message(int(poll.id), message.id)
        await interaction.followup.send(
            embed=container.embeds.success("Sondage créé", "Le sondage a été publié."),
            ephemeral=True,
        )

    def _ensure_staff(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
