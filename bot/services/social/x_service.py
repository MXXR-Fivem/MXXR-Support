from __future__ import annotations

from datetime import datetime

import httpx

from bot.models.domain import SocialPost


class XService:
    platform = "x"

    def __init__(self, bearer_token: str | None, user_ids: list[str], http_client: httpx.AsyncClient) -> None:
        self.bearer_token = bearer_token
        self.user_ids = user_ids
        self.http_client = http_client

    async def fetch_new_posts(self) -> list[SocialPost]:
        """Fetch recent X posts for the configured user IDs through the X API.

        ## Parameters
            - None.

        ## Returns
            A list of recent X posts collected from configured user identifiers.
        """

        if not self.bearer_token or not self.user_ids:
            return []

        posts: list[SocialPost] = []
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        for user_id in self.user_ids:
            response = await self.http_client.get(
                f"https://api.twitter.com/2/users/{user_id}/tweets",
                params={
                    "exclude": "replies,retweets",
                    "max_results": 5,
                    "tweet.fields": "created_at,text",
                },
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("data", []):
                posts.append(
                    SocialPost(
                        platform=self.platform,
                        external_id=item["id"],
                        title=f"Nouveau post X • {user_id}",
                        url=f"https://x.com/i/web/status/{item['id']}",
                        summary=item.get("text"),
                        published_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                    )
                )
        return posts
