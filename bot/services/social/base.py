from __future__ import annotations

from typing import Protocol

from bot.models.domain import SocialPost


class SocialFetcher(Protocol):
    platform: str

    async def fetch_new_posts(self) -> list[SocialPost]:
        """Fetch newly discovered social posts from a platform-specific provider.

        ## Parameters
            - None.

        ## Returns
            A list of newly discovered posts for the platform.
        """

        ...
