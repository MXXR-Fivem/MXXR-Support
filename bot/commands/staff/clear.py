from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


def build_clear_success_embed(container: BotContainer, deleted_count: int) -> discord.Embed:
    """Build the confirmation embed shown after clearing messages.

    ## Parameters
        - container: Central application services and configuration container.
        - deleted_count: Number of deleted messages.

    ## Returns
        A branded success embed.
    """

    label = "message supprimé" if deleted_count == 1 else "messages supprimés"
    return container.embeds.success("Nettoyage terminé", f"`{deleted_count}` {label} dans le salon.")
