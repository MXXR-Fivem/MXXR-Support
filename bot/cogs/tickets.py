from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.staff.tickets import build_ticket_panel_embed
from bot.guards.checks import has_staff_permissions
from bot.views.ticket_views import TicketCloseView, TicketPanelView

if TYPE_CHECKING:
    from bot.app import ShopBot


class TicketsCog(commands.Cog):
    def __init__(self, bot: ShopBot) -> None:
        self.bot = bot

    @app_commands.command(name="ticket-create", description="Ouvre un ticket de support")
    async def ticket_create(self, interaction: discord.Interaction, category_key: str, reason: str) -> None:
        container = self.bot.container
        assert container is not None
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            raise RuntimeError("Guild member context is required.")

        try:
            ticket, channel = await container.tickets.create_ticket(
                guild=interaction.guild,
                author=interaction.user,
                category_key=category_key,
                reason=reason,
            )
        except ValueError as error:
            await interaction.response.send_message(
                embed=container.embeds.error("Impossible de créer le ticket", str(error)),
                ephemeral=True,
            )
            return
        opening_embed = await container.tickets.build_opening_embed(ticket, interaction.user)
        await channel.send(
            content=f"{interaction.user.mention} {container.tickets.build_support_ping()}".strip(),
            embed=opening_embed,
            view=TicketCloseView(),
        )
        log_embed = await container.tickets.build_log_embed(ticket=ticket, author=interaction.user)
        await container.tickets.send_log_embed(interaction.guild, log_embed)

        await interaction.response.send_message(
            embed=container.embeds.success("Ticket créé", f"Votre ticket a été créé: {channel.mention}"),
            ephemeral=True,
        )

    @app_commands.command(name="ticket-panel", description="Publie le panneau de création de ticket")
    async def ticket_panel(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        await self._enforce_staff(interaction)
        embed = build_ticket_panel_embed(container)
        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message(
            embed=container.embeds.success("Panneau publié", "Le panneau de tickets a été publié."),
            ephemeral=True,
        )

    @ticket_create.autocomplete("category_key")
    async def ticket_category_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        container = self.bot.container
        assert container is not None
        categories = container.config.tickets.categories
        return [
            app_commands.Choice(name=f"{item.label} ({item.key})", value=item.key)
            for item in categories
            if current.lower() in item.label.lower() or current.lower() in item.key.lower()
        ][:25]

    async def _enforce_staff(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        if not isinstance(interaction.user, discord.Member):
            raise app_commands.CheckFailure("Contexte membre requis.")
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
