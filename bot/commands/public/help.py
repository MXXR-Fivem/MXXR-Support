from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


def build_help_embed(container: BotContainer, interaction: discord.Interaction) -> discord.Embed:
    """Build the branded help embed for public commands.

    ## Parameters
        - container: Central application services and configuration container.
        - interaction: Current interaction.

    ## Returns
        A branded help embed for public commands.
    """

    embed = container.embeds.info("Centre d'aide", "Liste des commandes principales du bot.")
    public_commands = [
        "`/help` • Affiche l'aide",
        "`/avatar` • Affiche l'avatar d'un membre",
        "`/info` • Affiche les informations de la boutique",
        "`/ping` • Affiche la latence du bot",
        "`/ticket-create` • Ouvre un ticket",
    ]
    embed.add_field(name="Commandes publiques", value="\n".join(public_commands), inline=False)
    return embed
