from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import discord
import httpx
import pytest

from bot.commands.staff.social import build_social_post_embed, resolve_social_preview_image
from bot.config.models import BrandingConfig
from bot.embeds.factory import EmbedFactory
from bot.models.domain import GiveawayRecord
from bot.services.giveaway_service import GiveawayService
from bot.tasks.giveaway_watch import GiveawayWatcherTask


@pytest.mark.asyncio
async def test_resolve_social_preview_image_uses_youtube_thumbnail_without_http_call() -> None:
    async with httpx.AsyncClient() as client:
        preview_url = await resolve_social_preview_image(client, "youtube", "https://youtu.be/dQw4w9WgXcQ")

    assert preview_url == "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"


@pytest.mark.asyncio
async def test_resolve_social_preview_image_reads_open_graph_image() -> None:
    html = """
    <html>
      <head>
        <meta property="og:image" content="https://cdn.example.com/preview.jpg">
      </head>
    </html>
    """

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        preview_url = await resolve_social_preview_image(client, "x", "https://x.com/example/status/123")

    assert preview_url == "https://cdn.example.com/preview.jpg"


@pytest.mark.asyncio
async def test_resolve_social_preview_image_uses_tiktok_oembed_fallback() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://www.tiktok.com/video/example":
            return httpx.Response(200, text="<html></html>")
        if str(request.url) == "https://www.tiktok.com/oembed?url=https%3A%2F%2Fwww.tiktok.com%2Fvideo%2Fexample":
            return httpx.Response(200, json={"thumbnail_url": "https://cdn.example.com/tiktok.jpg"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        preview_url = await resolve_social_preview_image(client, "tiktok", "https://www.tiktok.com/video/example")

    assert preview_url == "https://cdn.example.com/tiktok.jpg"


def test_build_social_post_embed_sets_preview_image_when_available() -> None:
    container = SimpleNamespace(embeds=EmbedFactory(BrandingConfig()))

    embed = build_social_post_embed(
        container=container,
        platform="youtube",
        title="Titre",
        url="https://youtube.com/watch?v=abc",
        summary="Resume",
        published_at=datetime.now(timezone.utc),
        preview_image_url="https://cdn.example.com/preview.jpg",
    )

    assert isinstance(embed, discord.Embed)
    assert embed.image.url == "https://cdn.example.com/preview.jpg"


class FakeMessage:
    def __init__(self, message_id: int) -> None:
        self.id = message_id
        self.deleted = False

    async def delete(self) -> None:
        self.deleted = True


class FakeChannel:
    def __init__(self, message: FakeMessage) -> None:
        self._message = message
        self.sent_messages: list[SimpleNamespace] = []

    async def fetch_message(self, message_id: int) -> FakeMessage:
        assert message_id == self._message.id
        return self._message

    async def send(self, content: str | None = None, embed: object | None = None) -> SimpleNamespace:
        sent_message = SimpleNamespace(id=987654321, content=content, embed=embed)
        self.sent_messages.append(sent_message)
        return sent_message


class FakeDatabase:
    def __init__(self, giveaway: GiveawayRecord) -> None:
        self.giveaway = giveaway
        self.updated_message_id: int | None = None
        self.updated_winner_ids: list[int] | None = None

    async def get_active_giveaways_due(self, _: datetime) -> list[GiveawayRecord]:
        return [self.giveaway]

    async def count_giveaway_entries(self, _: int) -> int:
        return 0

    async def set_giveaway_message(self, _: int, message_id: int) -> None:
        self.updated_message_id = message_id

    async def get_giveaway_entries(self, _: int) -> list[int]:
        return [100, 200]

    async def set_giveaway_winners(self, _: int, winner_ids: list[int]) -> None:
        self.updated_winner_ids = winner_ids


class FakeGiveawaysService:
    async def finalize_giveaway(self, _: GiveawayRecord) -> list[int]:
        return []

    def build_results_embed(self, _: GiveawayRecord, __: list[int], participant_count: int | None = None) -> str:
        return f"participants={participant_count}"


@pytest.mark.asyncio
async def test_giveaway_reroll_updates_stored_winners() -> None:
    giveaway = GiveawayRecord(
        id=1,
        guild_id=1,
        channel_id=10,
        message_id=42,
        host_id=99,
        title="Test",
        description="Desc",
        winner_count=1,
        ends_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        status="ended",
        winner_ids=[100],
    )
    database = FakeDatabase(giveaway)
    service = GiveawayService(database, EmbedFactory(BrandingConfig()))
    winners = await service.reroll_giveaway(giveaway)

    assert winners == [200]
    assert giveaway.winner_ids == [200]
    assert database.updated_winner_ids == [200]


class FakeBot:
    def __init__(self, channel: FakeChannel) -> None:
        self._channel = channel

    def get_channel(self, _: int) -> FakeChannel:
        return self._channel


@pytest.mark.asyncio
async def test_giveaway_watcher_deletes_original_message_before_posting_results(monkeypatch: pytest.MonkeyPatch) -> None:
    giveaway = GiveawayRecord(
        id=1,
        guild_id=1,
        channel_id=10,
        message_id=42,
        host_id=99,
        title="Test",
        description="Desc",
        winner_count=1,
        ends_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    original_message = FakeMessage(42)
    channel = FakeChannel(original_message)
    database = FakeDatabase(giveaway)
    container = SimpleNamespace(database=database, giveaways=FakeGiveawaysService())
    watcher = GiveawayWatcherTask(FakeBot(channel), container)
    monkeypatch.setattr("bot.tasks.giveaway_watch.discord.TextChannel", FakeChannel)

    await watcher.runner.coro(watcher)

    assert original_message.deleted is True
    assert len(channel.sent_messages) == 1
    assert database.updated_message_id == 987654321
