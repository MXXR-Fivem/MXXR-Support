from __future__ import annotations

from datetime import timedelta

import discord

from bot.config.models import AppConfig
from bot.embeds.factory import EmbedFactory
from bot.storage.database import Database
from bot.utils.time import utcnow


class BanProtectionService:
    def __init__(self, database: Database, config: AppConfig, embed_factory: EmbedFactory) -> None:
        self.database = database
        self.config = config
        self.embed_factory = embed_factory

    async def record_ban_and_check_limit(
        self,
        guild: discord.Guild,
        actor: discord.Member,
        target_id: int,
    ) -> tuple[bool, int]:
        """Record a ban action and enforce the configured anti-abuse threshold.

        ## Parameters
            - guild: Guild where the ban happened.
            - actor: Moderator who executed the ban.
            - target_id: Banned user identifier.

        ## Returns
            A tuple containing whether the threshold was exceeded and the current count.
        """

        now = utcnow()
        await self.database.record_ban_action(guild.id, actor.id, target_id, now)
        since = now - timedelta(minutes=self.config.ban_protection.window_minutes)
        count = await self.database.count_ban_actions_since(guild.id, actor.id, since)
        limit_exceeded = count > self.config.ban_protection.max_bans_per_window
        if limit_exceeded:
            roles_to_remove = [guild.get_role(role_id) for role_id in self.config.roles.ban_authorized]
            roles_to_remove = [role for role in roles_to_remove if role is not None]
            if roles_to_remove:
                await actor.remove_roles(*roles_to_remove, reason="Ban protection threshold exceeded")
        return limit_exceeded, count

    def build_alert_embed(self, actor: discord.Member, count: int) -> discord.Embed:
        """Build the branded alert embed sent when ban abuse protection triggers.

        ## Parameters
            - actor: Moderator who crossed the configured ban threshold.
            - count: Number of bans recorded during the sliding window.

        ## Returns
            A branded moderation alert embed.
        """

        removed_roles = " ".join(f"<@&{role_id}>" for role_id in self.config.roles.ban_authorized)
        description = (
            f"{actor.mention} a dépassé la limite de bans autorisés.\n"
            f"Les rôles {removed_roles} ont été retirés automatiquement."
        )
        embed = self.embed_factory.moderation("Protection anti-abus déclenchée", description)
        embed.add_field(name="Bans récents", value=str(count), inline=True)
        embed.add_field(
            name="Fenêtre",
            value=f"{self.config.ban_protection.window_minutes} minute(s)",
            inline=True,
        )
        return embed
