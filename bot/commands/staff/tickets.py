from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


def build_ticket_panel_embed(container: BotContainer) -> discord.Embed:
    """Build the branded embed used for the public ticket creation panel.

    ## Parameters
        - container: Central application services and configuration container.

    ## Returns
        A branded embed inviting users to open a support ticket.
    """

    categories = "\n".join(
        f"{item.emoji} **{item.label}** • {item.description}"
        for item in container.config.tickets.categories
    )
    embed = container.embeds.ticket(
        "Support boutique",
        "Utilisez le bouton ci-dessous pour créer un ticket privé avec le support.",
    )
    embed.add_field(name="Catégories", value=categories or "Aucune catégorie configurée.", inline=False)
    return embed
