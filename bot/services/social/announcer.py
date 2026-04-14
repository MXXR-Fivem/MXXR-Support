from __future__ import annotations

import discord

from bot.embeds.factory import EmbedFactory
from bot.models.domain import SocialPost
from bot.services.social.base import SocialFetcher
from bot.storage.database import Database
from bot.utils.time import format_datetime


class SocialAnnouncerService:
    def __init__(
        self,
        database: Database,
        embed_factory: EmbedFactory,
        fetchers: list[SocialFetcher],
    ) -> None:
        self.database = database
        self.embed_factory = embed_factory
        self.fetchers = fetchers

    async def collect_unpublished_posts(self) -> list[SocialPost]:
        """Collect social posts that have not yet been published to Discord.

        ## Parameters
            - None.

        ## Returns
            A list of social posts that were not announced before.
        """

        new_posts: list[SocialPost] = []
        for fetcher in self.fetchers:
            for post in await fetcher.fetch_new_posts():
                if not await self.database.has_social_post(post.platform, post.external_id):
                    new_posts.append(post)
        new_posts.sort(key=lambda item: item.published_at)
        return new_posts

    async def mark_as_published(self, post: SocialPost) -> None:
        """Mark a social post as published so it is not announced twice.

        ## Parameters
            - post: Social post that has just been published to Discord.

        ## Returns
            None.
        """

        await self.database.store_social_post(post.platform, post.external_id, post.published_at)

    def build_embed(self, post: SocialPost) -> discord.Embed:
        """Build the branded embed used for a social announcement post.

        ## Parameters
            - post: Social post to format into a Discord embed.

        ## Returns
            A branded social announcement embed.
        """

        description = post.summary or "Un nouveau contenu est disponible."
        embed = self.embed_factory.social_post(post.title, description[:4096])
        embed.add_field(name="Plateforme", value=post.platform.title(), inline=True)
        embed.add_field(name="Publié le", value=format_datetime(post.published_at), inline=True)
        embed.add_field(name="Lien", value=post.url, inline=False)
        return embed
