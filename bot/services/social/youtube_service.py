from __future__ import annotations

from datetime import datetime

import httpx

from bot.models.domain import SocialPost


class YouTubeService:
    platform = "youtube"

    def __init__(self, api_key: str | None, channel_ids: list[str], http_client: httpx.AsyncClient) -> None:
        self.api_key = api_key
        self.channel_ids = channel_ids
        self.http_client = http_client

    async def fetch_new_posts(self) -> list[SocialPost]:
        """Fetch recent YouTube videos for the configured channel IDs.

        ## Parameters
            - None.

        ## Returns
            A list of recent YouTube video posts collected from configured channels.
        """

        if not self.api_key or not self.channel_ids:
            return []

        posts: list[SocialPost] = []
        for channel_id in self.channel_ids:
            response = await self.http_client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "channelId": channel_id,
                    "maxResults": 5,
                    "order": "date",
                    "type": "video",
                    "key": self.api_key,
                },
            )
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]
                posts.append(
                    SocialPost(
                        platform=self.platform,
                        external_id=video_id,
                        title=snippet["title"],
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        summary=snippet.get("description"),
                        published_at=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")),
                    )
                )
        return posts
