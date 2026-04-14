from __future__ import annotations

from typing import Iterable

import discord

from bot.config.models import BrandingConfig


class EmbedFactory:
    def __init__(self, branding: BrandingConfig) -> None:
        self.branding = branding
        self.color = discord.Color.from_str(branding.primary_color)

    def _base(self, title: str, description: str, icon: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"{icon} {title}",
            description=description,
            color=self.color,
        )
        if self.branding.footer_icon_url:
            embed.set_footer(text=self.branding.footer_text, icon_url=self.branding.footer_icon_url)
        else:
            embed.set_footer(text=self.branding.footer_text)
        return embed

    def success(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "✅")

    def error(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "❌")

    def warning(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "⚠️")

    def info(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "ℹ️")

    def ticket(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "🎫")

    def review(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "⭐")

    def poll(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "📊")

    def giveaway(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "🎉")

    def moderation(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "🛡️")

    def social_post(self, title: str, description: str) -> discord.Embed:
        return self._base(title, description, "📣")

    def add_fields(
        self,
        embed: discord.Embed,
        fields: Iterable[tuple[str, str, bool]],
    ) -> discord.Embed:
        """Append a batch of standardized fields to an existing embed.

        ## Parameters
            - embed: Embed instance to enrich with fields.
            - fields: Sequence of tuples containing name, value, and inline flag.

        ## Returns
            The updated embed instance.
        """

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        return embed
