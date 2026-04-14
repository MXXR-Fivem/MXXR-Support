from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


def build_ping_embed(container: BotContainer, latency_ms: int) -> discord.Embed:
    """Build the bot latency embed.

    ## Parameters
        - container: Central application services and configuration container.
        - latency_ms: Current websocket latency in milliseconds.

    ## Returns
        A branded informational embed showing the measured latency.
    """

    return container.embeds.info("Ping", f"Latence actuelle du bot: `{latency_ms} ms`.")
