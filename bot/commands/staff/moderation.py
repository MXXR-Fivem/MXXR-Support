from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


def build_ban_success_embed(container: BotContainer, target: discord.abc.User, reason: str) -> discord.Embed:
    """Build the branded confirmation embed shown after a successful ban.

    ## Parameters
        - container: Central application services and configuration container.
        - target: Banned user object.
        - reason: Ban reason.

    ## Returns
        A branded confirmation embed.
    """

    embed = container.embeds.moderation("Membre banni", f"{target.mention} a été banni via le bot.")
    embed.add_field(name="Raison", value=reason, inline=False)
    return embed
