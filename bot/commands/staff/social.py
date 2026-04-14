from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

import discord

from bot.utils.time import format_datetime

if TYPE_CHECKING:
    from bot.app import BotContainer


SocialPlatform = Literal["youtube", "x", "tiktok"]

PLATFORM_LABELS: dict[SocialPlatform, str] = {
    "youtube": "YouTube",
    "x": "X",
    "tiktok": "TikTok",
}


def build_social_post_embed(
    container: BotContainer,
    platform: SocialPlatform,
    title: str,
    url: str,
    summary: str | None,
    published_at: datetime,
) -> discord.Embed:
    """Build the embed used for a manually published social post.

    ## Parameters
        - container: Central application services and configuration container.
        - platform: Social platform selected by the staff user.
        - title: Post title displayed in the embed.
        - url: Target content URL.
        - summary: Optional content summary.
        - published_at: Publication timestamp shown in the embed.

    ## Returns
        A branded embed ready to be posted in Discord.
    """

    label = PLATFORM_LABELS[platform]
    description = (summary or "Un nouveau contenu est disponible.")[:4096]
    embed = container.embeds.social_post(title, description)
    embed.add_field(name="Plateforme", value=label, inline=True)
    embed.add_field(name="Publié le", value=format_datetime(published_at), inline=True)
    embed.add_field(name="Lien", value=url, inline=False)
    return embed
