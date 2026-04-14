from __future__ import annotations

from typing import TYPE_CHECKING, cast

import discord

from bot.services.ticket_service import TicketService

if TYPE_CHECKING:
    from bot.app import ShopBot


def get_bot(interaction: discord.Interaction) -> ShopBot:
    """Resolve and validate the custom ShopBot instance from an interaction client.

    ## Parameters
        - interaction: Interaction whose client must be resolved to the custom bot type.

    ## Returns
        The ShopBot instance bound to the interaction.
    """

    client = interaction.client
    if client is None or not hasattr(client, "container"):
        raise RuntimeError("Invalid bot client.")
    return cast("ShopBot", client)


class TicketCategorySelect(discord.ui.Select):
    def __init__(self, ticket_service: TicketService) -> None:
        options = [
            discord.SelectOption(
                label=category.label,
                value=category.key,
                description=category.description[:100],
                emoji=category.emoji,
            )
            for category in ticket_service.config.tickets.categories
        ]
        super().__init__(
            placeholder="Choisissez une catégorie",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket:select-category",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = get_bot(interaction)
        container = bot.container
        assert container is not None
        if not isinstance(interaction.user, discord.Member) or interaction.guild is None:
            raise RuntimeError("Member context is required.")

        category_key = self.values[0]
        try:
            ticket, channel = await container.tickets.create_ticket(
                guild=interaction.guild,
                author=interaction.user,
                category_key=category_key,
                reason="Ticket créé depuis le panneau.",
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

        embed = container.embeds.success("Ticket créé", f"Votre ticket a été créé: {channel.mention}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class TicketCategoryView(discord.ui.View):
    def __init__(self, ticket_service: TicketService) -> None:
        super().__init__(timeout=120)
        self.add_item(TicketCategorySelect(ticket_service))


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Créer un ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="ticket:create",
    )
    async def create_ticket_button(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        bot = get_bot(interaction)
        container = bot.container
        assert container is not None
        view = TicketCategoryView(container.tickets)
        embed = container.embeds.ticket(
            "Choix de la catégorie",
            "Sélectionnez la catégorie correspondant à votre demande.",
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class TicketCloseView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fermer le ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="ticket:close",
    )
    async def close_ticket_button(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        bot = get_bot(interaction)
        container = bot.container
        assert container is not None
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            raise RuntimeError("Invalid ticket channel.")
        transcript_path = await container.tickets.close_ticket(channel, interaction.user)
        ticket = await container.database.get_ticket_by_channel(channel.id)
        if interaction.guild and ticket is not None:
            author = interaction.guild.get_member(ticket.author_id)
            log_embed = await container.tickets.build_log_embed(
                ticket=ticket,
                author=author,
                closed_by=interaction.user,
                transcript_path=transcript_path,
            )
            await container.tickets.send_log_embed(interaction.guild, log_embed)

        embed = container.embeds.warning("Ticket fermé", "Le salon sera supprimé dans quelques secondes.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await channel.delete(reason=f"Ticket fermé par {interaction.user} ({interaction.user.id})")
