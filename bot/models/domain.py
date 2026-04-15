from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TicketRecord(BaseModel):
    id: int | None = None
    guild_id: int
    channel_id: int
    author_id: int
    category_key: str
    reason: str
    status: str = "open"
    created_at: datetime
    closed_at: datetime | None = None
    closed_by_id: int | None = None
    transcript_path: str | None = None


class GiveawayRecord(BaseModel):
    id: int | None = None
    guild_id: int
    channel_id: int
    message_id: int | None = None
    host_id: int
    title: str
    description: str
    winner_count: int
    ends_at: datetime
    ended_at: datetime | None = None
    status: str = "active"
    winner_ids: list[int] = Field(default_factory=list)


class ReviewRecord(BaseModel):
    id: int | None = None
    guild_id: int
    author_id: int
    author_name: str
    scripts: str
    rating: int
    comment: str
    translated: str | None = None
    created_at: datetime
    source_message_id: int | None = None
    posted_message_id: int | None = None
    content_cleaned: bool = False


class PollRecord(BaseModel):
    id: int | None = None
    guild_id: int
    channel_id: int
    message_id: int | None = None
    author_id: int
    question: str
    description: str
    options: list[str]
    ends_at: datetime
    created_at: datetime
    status: str = "active"
    ended_at: datetime | None = None


class TebexPaymentRecord(BaseModel):
    id: int
    status: str
    email: str | None = None
    amount: str | None = None
    date: datetime
    player_id: int | None = None
    player_name: str | None = None
    player_uuid: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class TebexMetrics(BaseModel):
    total_sales: int
    unique_customers: int
    refreshed_at: datetime
