from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiohttp import web

from bot.config.settings import EnvironmentSettings
from bot.services.review_service import clean_review_text

if TYPE_CHECKING:
    from bot.storage.database import Database

logger = logging.getLogger(__name__)


class ReviewApiService:
    def __init__(self, settings: EnvironmentSettings, database: "Database") -> None:
        self.settings = settings
        self.database = database
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

    def enabled(self) -> bool:
        return bool(self.settings.review_api_bearer_token)

    async def start(self) -> None:
        if not self.enabled():
            return

        app = web.Application(middlewares=[self._auth_middleware])
        app.router.add_get("/api/reviews/random", self.get_random_reviews)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(
            self.runner,
            host=self.settings.review_api_host,
            port=self.settings.review_api_port,
        )
        await self.site.start()
        logger.info(
            "Review API listening on %s:%s",
            self.settings.review_api_host,
            self.settings.review_api_port,
        )

    async def stop(self) -> None:
        if self.runner is not None:
            await self.runner.cleanup()
            self.runner = None
            self.site = None

    @web.middleware
    async def _auth_middleware(self, request: web.Request, handler):
        expected_token = self.settings.review_api_bearer_token
        authorization = request.headers.get("Authorization", "")
        if expected_token is None or authorization != f"Bearer {expected_token}":
            return web.json_response({"error": "unauthorized"}, status=401)
        return await handler(request)

    async def get_random_reviews(self, request: web.Request) -> web.Response:
        raw_limit = request.query.get("limit", "5")
        try:
            limit = max(1, min(int(raw_limit), 50))
        except ValueError:
            return web.json_response({"error": "invalid_limit"}, status=400)

        reviews = await self.database.get_random_reviews(limit)
        for review in reviews:
            if not review.content_cleaned and review.id is not None:
                review.comment = clean_review_text(review.comment)
                review.translated = clean_review_text(review.translated) if review.translated else None
                review.content_cleaned = True
                await self.database.update_review_content(
                    int(review.id),
                    review.comment,
                    review.translated,
                    content_cleaned=True,
                )
        payload = {
            "count": len(reviews),
            "reviews": [
                {
                    "id": review.id,
                    "author_name": review.author_name,
                    "scripts": review.scripts,
                    "rating": review.rating,
                    "comment_fr": review.comment,
                    "comment_en": review.translated or review.comment,
                    "content_cleaned": review.content_cleaned,
                    "created_at": review.created_at.isoformat(),
                }
                for review in reviews
            ],
        }
        return web.json_response(payload)
