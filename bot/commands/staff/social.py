from __future__ import annotations

from datetime import datetime
from html import unescape
import re
from typing import TYPE_CHECKING, Literal
from urllib.parse import quote

import discord
import httpx

from bot.commands.staff.announcements import _extract_youtube_video_id
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
    preview_image_url: str | None = None,
) -> discord.Embed:
    """Build the embed used for a manually published social post.

    ## Parameters
        - container: Central application services and configuration container.
        - platform: Social platform selected by the staff user.
        - title: Post title displayed in the embed.
        - url: Target content URL.
        - summary: Optional content summary.
        - published_at: Publication timestamp shown in the embed.
        - preview_image_url: Optional preview image displayed in the embed.

    ## Returns
        A branded embed ready to be posted in Discord.
    """

    label = PLATFORM_LABELS[platform]
    description = (summary or "Un nouveau contenu est disponible.")[:4096]
    embed = container.embeds.social_post(title, description)
    embed.add_field(name="Plateforme", value=label, inline=True)
    embed.add_field(name="Publié le", value=format_datetime(published_at), inline=True)
    embed.add_field(name="Lien", value=url, inline=False)
    if preview_image_url:
        embed.set_image(url=preview_image_url)
    return embed


async def resolve_social_preview_image(
    http_client: httpx.AsyncClient,
    platform: SocialPlatform,
    url: str,
) -> str | None:
    if platform == "youtube":
        return _get_youtube_preview_image(url)
    if platform == "x":
        return await _fetch_open_graph_image(http_client, url)
    if platform == "tiktok":
        preview_image_url = await _fetch_open_graph_image(http_client, url)
        if preview_image_url:
            return preview_image_url
        return await _fetch_tiktok_oembed_image(http_client, url)
    return None


def _get_youtube_preview_image(url: str) -> str | None:
    video_id = _extract_youtube_video_id(url)
    if video_id is None:
        return None
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"


async def _fetch_open_graph_image(http_client: httpx.AsyncClient, url: str) -> str | None:
    try:
        response = await http_client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    html = response.text
    patterns = (
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
        r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image(?::src)?["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return unescape(match.group(1))
    return None


async def _fetch_tiktok_oembed_image(http_client: httpx.AsyncClient, url: str) -> str | None:
    try:
        response = await http_client.get(
            f"https://www.tiktok.com/oembed?url={quote(url, safe='')}",
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None
    thumbnail_url = payload.get("thumbnail_url")
    return str(thumbnail_url) if thumbnail_url else None
