from __future__ import annotations

import logging

import discord

from bot.config.models import AppConfig
from bot.constants.defaults import TRANSCRIPTS_DIR
from bot.embeds.factory import EmbedFactory
from bot.models.domain import TicketRecord
from bot.storage.database import Database
from bot.utils.discord import build_channel_overwrites, mention_roles
from bot.utils.time import format_datetime, utcnow

logger = logging.getLogger(__name__)


class TicketService:
    def __init__(self, database: Database, config: AppConfig, embed_factory: EmbedFactory) -> None:
        self.database = database
        self.config = config
        self.embed_factory = embed_factory

    async def create_ticket(
        self,
        guild: discord.Guild,
        author: discord.Member,
        category_key: str,
        reason: str,
    ) -> tuple[TicketRecord, discord.TextChannel]:
        """Create a private support ticket channel and persist its ticket record.

        ## Parameters
            - guild: Guild where the ticket channel must be created.
            - author: Member creating the ticket.
            - category_key: Configured ticket category key selected by the user.
            - reason: Free-text reason associated with the ticket.

        ## Returns
            The persisted ticket record and the created Discord channel.
        """

        existing = await self.database.get_open_ticket_by_author(guild.id, author.id)
        open_ticket_count = await self.database.count_open_tickets_by_author(guild.id, author.id)
        if open_ticket_count >= self.config.tickets.max_open_tickets_per_user and existing is not None:
            channel = guild.get_channel(existing.channel_id)
            if isinstance(channel, discord.TextChannel):
                raise ValueError(f"Vous avez déjà un ticket ouvert: {channel.mention}")
            raise ValueError("Vous avez déjà atteint la limite de tickets ouverts.")

        category_config = self.get_category(category_key)
        category_channel = guild.get_channel(self.config.channels.tickets_category)
        if not isinstance(category_channel, discord.CategoryChannel):
            raise RuntimeError("La catégorie de tickets configurée est introuvable.")

        overwrites = build_channel_overwrites(guild, author, self.config.roles.ticket_support)
        safe_name = "".join(char if char.isalnum() else "-" for char in author.display_name.lower())[:25].strip("-")
        channel_name = f"{category_config.key}-{safe_name or author.id}"
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category_channel,
            overwrites=overwrites,
            reason=f"Ticket créé par {author} ({author.id})",
        )

        ticket = TicketRecord(
            guild_id=guild.id,
            channel_id=channel.id,
            author_id=author.id,
            category_key=category_key,
            reason=reason,
            created_at=utcnow(),
        )
        ticket.id = await self.database.create_ticket(ticket)
        logger.info("Created ticket %s in channel %s", ticket.id, channel.id)
        return ticket, channel

    async def close_ticket(
        self,
        channel: discord.TextChannel,
        closed_by: discord.Member | discord.User,
    ) -> str | None:
        """Close a ticket channel, optionally export its transcript, and persist the closure.

        ## Parameters
            - channel: Ticket channel that must be closed.
            - closed_by: User responsible for the closure.

        ## Returns
            The transcript path when one was generated, otherwise None.
        """

        ticket = await self.database.get_ticket_by_channel(channel.id)
        if ticket is None:
            raise ValueError("Ce salon n'est pas un ticket enregistré.")

        transcript_path = None
        if self.config.tickets.transcript_enabled:
            transcript_path = await self._export_transcript(channel)
        await self.database.close_ticket(channel.id, closed_by.id, utcnow(), transcript_path)
        logger.info("Closed ticket channel %s by %s", channel.id, closed_by.id)
        return transcript_path

    def get_category(self, category_key: str):
        """Resolve a configured ticket category from its key.

        ## Parameters
            - category_key: Ticket category key to resolve from configuration.

        ## Returns
            The matching ticket category configuration.
        """

        for category in self.config.tickets.categories:
            if category.key == category_key:
                return category
        raise ValueError("Catégorie de ticket inconnue.")

    async def build_opening_embed(self, ticket: TicketRecord, author: discord.Member) -> discord.Embed:
        """Build the branded embed posted when a ticket channel is created.

        ## Parameters
            - ticket: Ticket record being announced inside the created channel.
            - author: Member who created the ticket.

        ## Returns
            A branded embed for the ticket opening message.
        """

        category = self.get_category(ticket.category_key)
        embed = self.embed_factory.ticket(
            title=f"Ticket {category.label}",
            description="Votre ticket a été créé. Un membre du staff vous répondra rapidement.",
        )
        self.embed_factory.add_fields(
            embed,
            (
                ("Auteur", author.mention, True),
                ("Catégorie", f"{category.emoji} {category.label}", True),
                ("Raison", ticket.reason, False),
            ),
        )
        return embed

    async def build_log_embed(
        self,
        ticket: TicketRecord,
        author: discord.Member | None,
        closed_by: discord.abc.User | None = None,
        transcript_path: str | None = None,
    ) -> discord.Embed:
        """Build a branded embed describing a ticket creation or closure event for logs.

        ## Parameters
            - ticket: Ticket record being logged.
            - author: Ticket owner when available from cache or guild lookup.
            - closed_by: Closing user when logging a closure event.
            - transcript_path: Optional transcript path to expose in the log.

        ## Returns
            A branded embed representing the ticket lifecycle event.
        """

        category = self.get_category(ticket.category_key)
        state = "Fermeture du ticket" if ticket.status == "closed" else "Création du ticket"
        description = f"Ticket `{ticket.channel_id}` lié à `{category.key}`."
        embed = self.embed_factory.ticket(state, description)
        self.embed_factory.add_fields(
            embed,
            (
                ("Auteur", author.mention if author else str(ticket.author_id), True),
                ("Catégorie", f"{category.emoji} {category.label}", True),
                ("Créé le", format_datetime(ticket.created_at), True),
                ("Raison", ticket.reason, False),
            ),
        )
        if closed_by is not None:
            embed.add_field(name="Fermé par", value=closed_by.mention, inline=True)
        if transcript_path:
            embed.add_field(name="Transcript", value=transcript_path, inline=False)
        return embed

    async def send_log_embed(self, guild: discord.Guild, embed: discord.Embed) -> None:
        """Send a ticket log embed without breaking the main ticket flow on log failures.

        ## Parameters
            - guild: Guild used to resolve the configured logs channel.
            - embed: Embed to post in the ticket logs channel.

        ## Returns
            None.
        """

        logs_channel = guild.get_channel(self.config.channels.tickets_logs)
        if not isinstance(logs_channel, discord.TextChannel):
            logger.warning("Ticket logs channel %s is missing or not a text channel", self.config.channels.tickets_logs)
            return
        try:
            await logs_channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning("Missing access to ticket logs channel %s", logs_channel.id)
        except discord.HTTPException:
            logger.exception("Failed to send ticket log embed to channel %s", logs_channel.id)

    def build_support_ping(self) -> str:
        """Build the role mention string used to notify support members in new tickets.

        ## Parameters
            - None.

        ## Returns
            A role mention string targeting support members when enabled.
        """

        if not self.config.tickets.mention_support_roles:
            return ""
        return mention_roles(self.config.roles.ticket_support)

    async def _export_transcript(self, channel: discord.TextChannel) -> str:
        """Export the full ticket message history to a transcript text file.

        ## Parameters
            - channel: Ticket channel whose message history should be exported.

        ## Returns
            Filesystem path to the transcript text file.
        """

        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        transcript_file = TRANSCRIPTS_DIR / f"ticket-{channel.id}.txt"
        lines: list[str] = []
        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = format_datetime(message.created_at)
            content = message.clean_content or "[message sans contenu]"
            lines.append(f"[{timestamp}] {message.author} ({message.author.id}): {content}")
        transcript_file.write_text("\n".join(lines), encoding="utf-8")
        return str(transcript_file.resolve())
