from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.staff.giveaways import build_giveaway_record
from bot.guards.checks import has_staff_permissions
from bot.utils.time import parse_duration_to_timedelta
from bot.views.giveaway_views import GiveawayJoinView

if TYPE_CHECKING:
    from bot.app import ShopBot


class GiveawaysCog(commands.Cog):
    def __init__(self, bot: ShopBot) -> None:
        self.bot = bot

    @app_commands.command(name="giveaway-create", description="Crée un giveaway")
    async def giveaway_create(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        duration: str,
        winner_count: app_commands.Range[int, 1, 20],
    ) -> None:
        container = self.bot.container
        assert container is not None
        self._ensure_staff(interaction)
        try:
            duration_delta = parse_duration_to_timedelta(duration)
        except ValueError as error:
            await interaction.response.send_message(
                embed=container.embeds.error("Durée invalide", str(error)),
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        giveaway = build_giveaway_record(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            host_id=interaction.user.id,
            title=title,
            description=description,
            duration=duration_delta,
            winner_count=winner_count,
        )
        await container.giveaways.create_giveaway(giveaway)
        message = await interaction.channel.send(
            embed=container.giveaways.build_giveaway_embed(giveaway, participant_count=0),
            view=GiveawayJoinView(),
        )
        await container.database.set_giveaway_message(int(giveaway.id), message.id)
        await interaction.followup.send(
            embed=container.embeds.success("Giveaway créé", f"Le giveaway a été publié dans {interaction.channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="giveaway-reroll", description="Relance le tirage d'un giveaway terminé")
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str) -> None:
        container = self.bot.container
        assert container is not None
        self._ensure_staff(interaction)
        giveaway = await container.database.get_giveaway_by_message(int(message_id))
        if giveaway is None or giveaway.status != "ended":
            raise app_commands.AppCommandError("Giveaway introuvable ou non terminé.")
        winners = await container.giveaways.reroll_giveaway(giveaway)
        participant_count = await container.database.count_giveaway_entries(int(giveaway.id))
        embed = container.giveaways.build_results_embed(giveaway, winners, participant_count=participant_count)
        await interaction.response.send_message(embed=embed)

    def _ensure_staff(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
