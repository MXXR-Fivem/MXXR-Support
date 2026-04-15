from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from bot.constants.defaults import DEFAULT_EMBED_COLOR, DEFAULT_EMBED_FOOTER


class BrandingConfig(BaseModel):
    shop_name: str = "MXXR Store"
    primary_color: str = DEFAULT_EMBED_COLOR
    footer_text: str = DEFAULT_EMBED_FOOTER
    footer_icon_url: str | None = None
    support_url: str | None = None
    tebex_url: str | None = None
    website_url: str | None = None
    discord_invite_url: str | None = None
    x_url: str | None = None
    youtube_url: str | None = None
    tiktok_url: str | None = None


class ChannelsConfig(BaseModel):
    logs: int
    reviews: int
    news: int
    pub_rp: int
    tickets_category: int
    tickets_logs: int


class RolesConfig(BaseModel):
    staff_bot: list[int]
    ban_authorized: list[int]
    customer: list[int] = Field(default_factory=list)
    moderation_exemptions: list[int] = Field(default_factory=list)
    ticket_support: list[int] = Field(default_factory=list)

    @field_validator("staff_bot", "ban_authorized", "customer", "moderation_exemptions", "ticket_support", mode="before")
    @classmethod
    def normalize_role_ids(cls, value: int | list[int]) -> list[int]:
        if isinstance(value, int):
            return [value]
        return value


class TicketCategoryConfig(BaseModel):
    key: str
    label: str
    emoji: str
    description: str


class TicketsConfig(BaseModel):
    max_open_tickets_per_user: int = 1
    categories: list[TicketCategoryConfig] = Field(default_factory=list)
    mention_support_roles: bool = True
    transcript_enabled: bool = True


class GiveawaysConfig(BaseModel):
    check_interval_seconds: int = 30


class PollsConfig(BaseModel):
    max_options: int = 5


class ModerationConfig(BaseModel):
    delete_discord_invites: bool = True


class BanProtectionConfig(BaseModel):
    max_bans_per_window: int = 5
    window_minutes: int = 60
    alert_channel_id: int | None = None


class PresenceConfig(BaseModel):
    enabled: bool = True
    switch_interval_seconds: int = 10
    refresh_interval_minutes: int = 15
    template: str = "{sales} ventes | {customers} clients"


class AppConfig(BaseModel):
    environment: Literal["development", "staging", "production"] = "development"
    branding: BrandingConfig = Field(default_factory=BrandingConfig)
    channels: ChannelsConfig
    roles: RolesConfig
    tickets: TicketsConfig = Field(default_factory=TicketsConfig)
    giveaways: GiveawaysConfig = Field(default_factory=GiveawaysConfig)
    polls: PollsConfig = Field(default_factory=PollsConfig)
    moderation: ModerationConfig = Field(default_factory=ModerationConfig)
    ban_protection: BanProtectionConfig = Field(default_factory=BanProtectionConfig)
    presence: PresenceConfig = Field(default_factory=PresenceConfig)

    @field_validator("polls")
    @classmethod
    def validate_polls(cls, value: PollsConfig) -> PollsConfig:
        if value.max_options < 2 or value.max_options > 5:
            raise ValueError("polls.max_options must be between 2 and 5")
        return value
