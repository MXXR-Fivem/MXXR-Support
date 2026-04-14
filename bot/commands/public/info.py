from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


async def build_info_embed(container: BotContainer) -> discord.Embed:
    """Build the branded information embed containing the store links and contact points.

    ## Parameters
        - container: Central application services and configuration container.

    ## Returns
        A branded informational embed for the store.
    """

    branding = container.config.branding
    embed = container.embeds.info(
        f"{branding.shop_name} • Informations",
        "Retrouvez ici tous les liens utiles de la boutique.",
    )
    fields: list[tuple[str, str, bool]] = []
    if branding.tebex_url:
        fields.append(("Boutique", branding.tebex_url, False))
    if branding.website_url:
        fields.append(("Site web", branding.website_url, False))
    if branding.discord_invite_url:
        fields.append(("Discord", branding.discord_invite_url, False))
    try:
        metrics = await container.tebex.get_metrics(force_refresh=True)
    except RuntimeError:
        metrics = None
    if metrics is not None:
        fields.append(
            (
                "Stats boutique",
                f"Ventes: `{metrics.total_sales}`\nClients: `{metrics.unique_customers}`",
                False,
            )
        )
    if branding.youtube_url or branding.x_url or branding.tiktok_url:
        social_lines = [
            line
            for line in (
                f"YouTube: {branding.youtube_url}" if branding.youtube_url else None,
                f"X: {branding.x_url}" if branding.x_url else None,
                f"TikTok: {branding.tiktok_url}" if branding.tiktok_url else None,
            )
            if line
        ]
        fields.append(("Réseaux sociaux", "\n".join(social_lines), False))
    return container.embeds.add_fields(embed, fields)
