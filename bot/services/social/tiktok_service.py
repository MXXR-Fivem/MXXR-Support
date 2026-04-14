from __future__ import annotations

from datetime import datetime

import httpx

from bot.models.domain import SocialPost


class TikTokService:
    platform = "tiktok"

    def __init__(self, external_feed_url: str | None, http_client: httpx.AsyncClient) -> None:
        self.external_feed_url = external_feed_url
        self.http_client = http_client

    async def fetch_new_posts(self) -> list[SocialPost]:
        """Fetch recent TikTok posts from the configured external JSON feed.

        ## Parameters
            - None.

        ## Returns
            Posts discovered from the configured external TikTok feed, if available.
        """

        if not self.external_feed_url:
            return []

        response = await self.http_client.get(self.external_feed_url)
        response.raise_for_status()
        payload = response.json()
        posts: list[SocialPost] = []
        for item in payload.get("items", []):
            posts.append(
                SocialPost(
                    platform=self.platform,
                    external_id=str(item["id"]),
                    title=item["title"],
                    url=item["url"],
                    summary=item.get("summary"),
                    published_at=datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")),
                )
            )
        return posts
