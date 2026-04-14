from __future__ import annotations

import re

import discord

from bot.config.models import AppConfig
from bot.embeds.factory import EmbedFactory

DISCORD_INVITE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com/invite)/[A-Za-z0-9-]+",
    re.IGNORECASE,
)


class ModerationService:
    def __init__(self, config: AppConfig, embed_factory: EmbedFactory) -> None:
        self.config = config
        self.embed_factory = embed_factory

    def should_delete_message(self, message: discord.Message) -> bool:
        """Determine whether a Discord message must be deleted for invite-link moderation.

        ## Parameters
            - message: Discord message to inspect.

        ## Returns
            True when the message should be deleted according to invite moderation rules.
        """

        if message.author.bot or not self.config.moderation.delete_discord_invites:
            return False
        if message.channel.id == self.config.channels.pub_rp:
            return False
        if not DISCORD_INVITE_RE.search(message.content):
            return False
        if isinstance(message.author, discord.Member):
            exempt_ids = set(self.config.roles.moderation_exemptions)
            if any(role.id in exempt_ids for role in message.author.roles):
                return False
        return True

    def build_log_embed(self, message: discord.Message) -> discord.Embed:
        """Build a branded moderation log embed for a deleted invite message.

        ## Parameters
            - message: Deleted message that triggered invite-link moderation.

        ## Returns
            A branded moderation log embed.
        """

        embed = self.embed_factory.moderation(
            "Lien Discord supprimé",
            "Un message contenant une invitation Discord non autorisée a été supprimé.",
        )
        embed.add_field(name="Auteur", value=message.author.mention, inline=True)
        embed.add_field(name="Salon", value=message.channel.mention, inline=True)
        embed.add_field(name="Contenu", value=message.content[:1024], inline=False)
        return embed
