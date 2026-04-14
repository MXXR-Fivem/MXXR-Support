from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from bot.models.domain import GiveawayRecord, PollRecord, ReviewRecord, TicketRecord


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the SQLite connection and initialize the database schema.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA journal_mode=WAL;")
        await self.connection.execute("PRAGMA foreign_keys=ON;")
        await self._create_tables()
        await self._migrate_tables()

    async def close(self) -> None:
        """Close the SQLite connection when the application stops.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        if self.connection is not None:
            await self.connection.close()

    async def _create_tables(self) -> None:
        assert self.connection is not None
        await self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL UNIQUE,
                author_id INTEGER NOT NULL,
                category_key TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                closed_at TEXT,
                closed_by_id INTEGER,
                transcript_path TEXT
            );

            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                host_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                winner_count INTEGER NOT NULL,
                ends_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL,
                winner_ids TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS giveaway_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giveaway_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(giveaway_id, user_id),
                FOREIGN KEY(giveaway_id) REFERENCES giveaways(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                scripts TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL,
                translated TEXT,
                created_at TEXT NOT NULL,
                source_message_id INTEGER,
                posted_message_id INTEGER,
                content_cleaned INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                author_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                description TEXT NOT NULL,
                options TEXT NOT NULL,
                ends_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS poll_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                option_index INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(poll_id, user_id),
                FOREIGN KEY(poll_id) REFERENCES polls(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ban_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                external_id TEXT NOT NULL,
                published_at TEXT NOT NULL,
                UNIQUE(platform, external_id)
            );

            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        await self.connection.commit()

    async def _migrate_tables(self) -> None:
        assert self.connection is not None
        cursor = await self.connection.execute("PRAGMA table_info(reviews)")
        review_columns = {row["name"] for row in await cursor.fetchall()}
        if "translated" not in review_columns:
            await self.connection.execute("ALTER TABLE reviews ADD COLUMN translated TEXT")
        if "source_message_id" not in review_columns:
            await self.connection.execute("ALTER TABLE reviews ADD COLUMN source_message_id INTEGER")
        if "posted_message_id" not in review_columns:
            await self.connection.execute("ALTER TABLE reviews ADD COLUMN posted_message_id INTEGER")
        if "content_cleaned" not in review_columns:
            await self.connection.execute("ALTER TABLE reviews ADD COLUMN content_cleaned INTEGER NOT NULL DEFAULT 0")
        await self.connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_source_message_id
            ON reviews(source_message_id)
            WHERE source_message_id IS NOT NULL
            """
        )
        cursor = await self.connection.execute("PRAGMA table_info(polls)")
        poll_columns = {row["name"] for row in await cursor.fetchall()}
        if "status" not in poll_columns:
            await self.connection.execute("ALTER TABLE polls ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        if "ended_at" not in poll_columns:
            await self.connection.execute("ALTER TABLE polls ADD COLUMN ended_at TEXT")
        await self.connection.execute(
            """
            UPDATE polls
            SET ends_at = created_at, status = 'ended', ended_at = created_at
            WHERE ends_at IS NULL
            """
        )
        await self.connection.commit()

    async def create_ticket(self, ticket: TicketRecord) -> int:
        """Persist a new ticket record in the database.

        ## Parameters
            - ticket: Ticket payload to persist in the database.

        ## Returns
            The created ticket identifier.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            INSERT INTO tickets (guild_id, channel_id, author_id, category_key, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket.guild_id,
                ticket.channel_id,
                ticket.author_id,
                ticket.category_key,
                ticket.reason,
                ticket.status,
                ticket.created_at.isoformat(),
            ),
        )
        await self.connection.commit()
        return int(cursor.lastrowid)

    async def get_open_ticket_by_author(self, guild_id: int, author_id: int) -> TicketRecord | None:
        """Fetch the most recent open ticket for a member in a guild.

        ## Parameters
            - guild_id: Guild identifier used to scope the search.
            - author_id: Member identifier owning the potential active ticket.

        ## Returns
            The matching open ticket or None.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            SELECT * FROM tickets
            WHERE guild_id = ? AND author_id = ? AND status = 'open'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (guild_id, author_id),
        )
        row = await cursor.fetchone()
        return self._row_to_ticket(row) if row else None

    async def count_open_tickets_by_author(self, guild_id: int, author_id: int) -> int:
        """Count how many tickets are currently open for a member in a guild.

        ## Parameters
            - guild_id: Guild identifier used to scope the search.
            - author_id: Member identifier owning the active tickets.

        ## Returns
            The number of currently open tickets for that member.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM tickets
            WHERE guild_id = ? AND author_id = ? AND status = 'open'
            """,
            (guild_id, author_id),
        )
        row = await cursor.fetchone()
        return int(row["total"]) if row else 0

    async def get_ticket_by_channel(self, channel_id: int) -> TicketRecord | None:
        """Fetch a ticket record by its Discord channel identifier.

        ## Parameters
            - channel_id: Ticket channel identifier.

        ## Returns
            The matching ticket or None.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT * FROM tickets WHERE channel_id = ? LIMIT 1",
            (channel_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_ticket(row) if row else None

    async def close_ticket(
        self,
        channel_id: int,
        closed_by_id: int,
        closed_at: datetime,
        transcript_path: str | None,
    ) -> None:
        """Mark a ticket as closed and store closure metadata.

        ## Parameters
            - channel_id: Ticket channel identifier being closed.
            - closed_by_id: Staff or member identifier closing the ticket.
            - closed_at: Timestamp of closure.
            - transcript_path: Optional filesystem path to the saved transcript.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            """
            UPDATE tickets
            SET status = 'closed', closed_by_id = ?, closed_at = ?, transcript_path = ?
            WHERE channel_id = ?
            """,
            (closed_by_id, closed_at.isoformat(), transcript_path, channel_id),
        )
        await self.connection.commit()

    async def create_giveaway(self, giveaway: GiveawayRecord) -> int:
        """Persist a newly created giveaway in the database.

        ## Parameters
            - giveaway: Giveaway payload to persist before publishing or scheduling.

        ## Returns
            The created giveaway identifier.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            INSERT INTO giveaways (guild_id, channel_id, host_id, title, description, winner_count, ends_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                giveaway.guild_id,
                giveaway.channel_id,
                giveaway.host_id,
                giveaway.title,
                giveaway.description,
                giveaway.winner_count,
                giveaway.ends_at.isoformat(),
                giveaway.status,
            ),
        )
        await self.connection.commit()
        return int(cursor.lastrowid)

    async def set_giveaway_message(self, giveaway_id: int, message_id: int) -> None:
        """Attach the published Discord message identifier to an existing giveaway.

        ## Parameters
            - giveaway_id: Giveaway identifier to update.
            - message_id: Discord message identifier storing the published giveaway.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            "UPDATE giveaways SET message_id = ? WHERE id = ?",
            (message_id, giveaway_id),
        )
        await self.connection.commit()

    async def add_giveaway_entry(self, giveaway_id: int, user_id: int, created_at: datetime) -> bool:
        """Insert a giveaway participation entry when it does not already exist.

        ## Parameters
            - giveaway_id: Giveaway identifier receiving a participant entry.
            - user_id: Member identifier joining the giveaway.
            - created_at: Participation timestamp.

        ## Returns
            True when a new entry was stored, otherwise False.
        """

        assert self.connection is not None
        try:
            await self.connection.execute(
                """
                INSERT INTO giveaway_entries (giveaway_id, user_id, created_at)
                VALUES (?, ?, ?)
                """,
                (giveaway_id, user_id, created_at.isoformat()),
            )
            await self.connection.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def remove_giveaway_entry(self, giveaway_id: int, user_id: int) -> bool:
        """Delete a giveaway participation entry for a member.

        ## Parameters
            - giveaway_id: Giveaway identifier from which the user should be removed.
            - user_id: Member identifier leaving the giveaway.

        ## Returns
            True when an entry was removed, otherwise False.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "DELETE FROM giveaway_entries WHERE giveaway_id = ? AND user_id = ?",
            (giveaway_id, user_id),
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def get_giveaway_entries(self, giveaway_id: int) -> list[int]:
        """Return every participant user ID registered for a giveaway.

        ## Parameters
            - giveaway_id: Giveaway identifier to inspect.

        ## Returns
            A list of participant user identifiers.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?",
            (giveaway_id,),
        )
        rows = await cursor.fetchall()
        return [int(row["user_id"]) for row in rows]

    async def count_giveaway_entries(self, giveaway_id: int) -> int:
        """Return the total number of participants registered for a giveaway.

        ## Parameters
            - giveaway_id: Giveaway identifier to inspect.

        ## Returns
            The number of registered participants.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT COUNT(*) AS total FROM giveaway_entries WHERE giveaway_id = ?",
            (giveaway_id,),
        )
        row = await cursor.fetchone()
        return int(row["total"]) if row else 0

    async def get_active_giveaways_due(self, now: datetime) -> list[GiveawayRecord]:
        """Fetch all active giveaways whose end time has already been reached.

        ## Parameters
            - now: Current timestamp used to filter overdue active giveaways.

        ## Returns
            Active giveaways whose end timestamp is reached.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            SELECT * FROM giveaways
            WHERE status = 'active' AND ends_at <= ?
            ORDER BY ends_at ASC
            """,
            (now.isoformat(),),
        )
        rows = await cursor.fetchall()
        return [self._row_to_giveaway(row) for row in rows]

    async def get_giveaway_by_message(self, message_id: int) -> GiveawayRecord | None:
        """Fetch a giveaway record from its published Discord message identifier.

        ## Parameters
            - message_id: Discord message identifier hosting the giveaway.

        ## Returns
            The matching giveaway or None.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT * FROM giveaways WHERE message_id = ? LIMIT 1",
            (message_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_giveaway(row) if row else None

    async def finish_giveaway(self, giveaway_id: int, ended_at: datetime, winner_ids: list[int]) -> None:
        """Mark a giveaway as ended and persist its winners.

        ## Parameters
            - giveaway_id: Giveaway identifier being finalized.
            - ended_at: Completion timestamp.
            - winner_ids: Selected Discord user identifiers.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            """
            UPDATE giveaways
            SET status = 'ended', ended_at = ?, winner_ids = ?
            WHERE id = ?
            """,
            (ended_at.isoformat(), json.dumps(winner_ids), giveaway_id),
        )
        await self.connection.commit()

    async def save_review(self, review: ReviewRecord) -> int:
        """Persist a customer review entry in the database.

        ## Parameters
            - review: Review payload to persist.

        ## Returns
            The created review identifier.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            INSERT INTO reviews (
                guild_id,
                author_id,
                author_name,
                scripts,
                rating,
                comment,
                translated,
                created_at,
                source_message_id,
                posted_message_id,
                content_cleaned
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review.guild_id,
                review.author_id,
                review.author_name,
                review.scripts,
                review.rating,
                review.comment,
                review.translated,
                review.created_at.isoformat(),
                review.source_message_id,
                review.posted_message_id,
                1 if review.content_cleaned else 0,
            ),
        )
        await self.connection.commit()
        return int(cursor.lastrowid)

    async def update_review_translation(self, review_id: int, translated: str, content_cleaned: bool | None = None) -> None:
        """Persist the translated English version of a review.

        ## Parameters
            - review_id: Review identifier to update.
            - translated: English translation to store.
            - content_cleaned: Optional normalized-content flag to store alongside the translation.

        ## Returns
            None.
        """

        assert self.connection is not None
        if content_cleaned is None:
            await self.connection.execute(
                "UPDATE reviews SET translated = ? WHERE id = ?",
                (translated, review_id),
            )
        else:
            await self.connection.execute(
                "UPDATE reviews SET translated = ?, content_cleaned = ? WHERE id = ?",
                (translated, 1 if content_cleaned else 0, review_id),
            )
        await self.connection.commit()

    async def update_review_content(
        self,
        review_id: int,
        comment: str,
        translated: str | None,
        content_cleaned: bool,
    ) -> None:
        """Persist normalized review text fields and their cleanup flag.

        ## Parameters
            - review_id: Review identifier to update.
            - comment: Cleaned French comment.
            - translated: Cleaned English translation when available.
            - content_cleaned: Whether the stored text fields are normalized.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            "UPDATE reviews SET comment = ?, translated = ?, content_cleaned = ? WHERE id = ?",
            (comment, translated, 1 if content_cleaned else 0, review_id),
        )
        await self.connection.commit()

    async def update_review_posted_message(self, review_id: int, posted_message_id: int) -> None:
        """Persist the Discord message identifier used to publish a review.

        ## Parameters
            - review_id: Review identifier to update.
            - posted_message_id: Discord message identifier in the reviews channel.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            "UPDATE reviews SET posted_message_id = ? WHERE id = ?",
            (posted_message_id, review_id),
        )
        await self.connection.commit()

    async def has_review_for_source_message(self, source_message_id: int) -> bool:
        """Return whether a legacy Discord message has already been imported as a review.

        ## Parameters
            - source_message_id: Discord message identifier from the legacy reviews channel.

        ## Returns
            True when a review already exists for that source message.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT 1 FROM reviews WHERE source_message_id = ? LIMIT 1",
            (source_message_id,),
        )
        return await cursor.fetchone() is not None

    async def get_reviews_missing_translation(self, limit: int) -> list[ReviewRecord]:
        """Return reviews that do not yet have a stored English translation.

        ## Parameters
            - limit: Maximum number of reviews to return.

        ## Returns
            Reviews missing their translated content.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            SELECT * FROM reviews
            WHERE translated IS NULL OR TRIM(translated) = ''
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_review(row) for row in rows]

    async def count_reviews_missing_translation(self) -> int:
        """Count reviews that do not yet have a stored English translation."""

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT COUNT(*) AS total FROM reviews WHERE translated IS NULL OR TRIM(translated) = ''"
        )
        row = await cursor.fetchone()
        return int(row["total"]) if row else 0

    async def get_random_reviews(self, limit: int) -> list[ReviewRecord]:
        """Return a random subset of reviews from the database.

        ## Parameters
            - limit: Maximum number of reviews to return.

        ## Returns
            Random reviews.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            SELECT * FROM reviews
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_review(row) for row in rows]

    async def get_reviews_missing_cleaning(self, limit: int) -> list[ReviewRecord]:
        """Return reviews whose stored text content has not yet been normalized.

        ## Parameters
            - limit: Maximum number of reviews to return.

        ## Returns
            Reviews still flagged as not cleaned.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            SELECT * FROM reviews
            WHERE content_cleaned = 0
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_review(row) for row in rows]

    async def count_reviews_missing_cleaning(self) -> int:
        """Count reviews whose stored text content has not yet been normalized."""

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT COUNT(*) AS total FROM reviews WHERE content_cleaned = 0"
        )
        row = await cursor.fetchone()
        return int(row["total"]) if row else 0

    async def get_review_by_id(self, review_id: int) -> ReviewRecord | None:
        """Fetch a review record by its database identifier.

        ## Parameters
            - review_id: Review identifier to retrieve.

        ## Returns
            The matching review or None.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT * FROM reviews WHERE id = ? LIMIT 1",
            (review_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_review(row) if row else None

    async def delete_review(self, review_id: int) -> bool:
        """Delete a review from the database.

        ## Parameters
            - review_id: Review identifier to delete.

        ## Returns
            True when a review row was deleted, otherwise False.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "DELETE FROM reviews WHERE id = ?",
            (review_id,),
        )
        await self.connection.commit()
        return cursor.rowcount > 0

    async def create_poll(self, poll: PollRecord) -> int:
        """Persist a newly created poll in the database.

        ## Parameters
            - poll: Poll payload to persist.

        ## Returns
            The created poll identifier.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            INSERT INTO polls (guild_id, channel_id, author_id, question, description, options, ends_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                poll.guild_id,
                poll.channel_id,
                poll.author_id,
                poll.question,
                poll.description,
                json.dumps(poll.options),
                poll.ends_at.isoformat() if poll.ends_at else None,
                poll.created_at.isoformat(),
            ),
        )
        await self.connection.commit()
        return int(cursor.lastrowid)

    async def set_poll_message(self, poll_id: int, message_id: int) -> None:
        """Attach the published Discord message identifier to an existing poll.

        ## Parameters
            - poll_id: Poll identifier to update.
            - message_id: Discord message identifier storing the published poll.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            "UPDATE polls SET message_id = ? WHERE id = ?",
            (message_id, poll_id),
        )
        await self.connection.commit()

    async def get_poll_by_message(self, message_id: int) -> PollRecord | None:
        """Fetch a poll record from its published Discord message identifier.

        ## Parameters
            - message_id: Discord message identifier hosting the poll.

        ## Returns
            The matching poll or None.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT * FROM polls WHERE message_id = ? LIMIT 1",
            (message_id,),
        )
        row = await cursor.fetchone()
        return self._row_to_poll(row) if row else None

    async def upsert_poll_vote(
        self,
        poll_id: int,
        user_id: int,
        option_index: int,
        created_at: datetime,
    ) -> None:
        """Insert or update a member vote for a poll.

        ## Parameters
            - poll_id: Poll identifier receiving the vote.
            - user_id: Member identifier casting the vote.
            - option_index: Chosen option index.
            - created_at: Vote timestamp.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            """
            INSERT INTO poll_votes (poll_id, user_id, option_index, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(poll_id, user_id)
            DO UPDATE SET option_index = excluded.option_index, created_at = excluded.created_at
            """,
            (poll_id, user_id, option_index, created_at.isoformat()),
        )
        await self.connection.commit()

    async def get_poll_results(self, poll_id: int) -> dict[int, int]:
        """Aggregate and return vote totals for each poll option.

        ## Parameters
            - poll_id: Poll identifier to aggregate.

        ## Returns
            A mapping of option index to vote count.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            SELECT option_index, COUNT(*) AS total
            FROM poll_votes
            WHERE poll_id = ?
            GROUP BY option_index
            """,
            (poll_id,),
        )
        rows = await cursor.fetchall()
        return {int(row["option_index"]): int(row["total"]) for row in rows}

    async def get_active_polls_due(self, now: datetime) -> list[PollRecord]:
        """Fetch all active polls whose end time has already been reached.

        ## Parameters
            - now: Current timestamp used to filter overdue active polls.

        ## Returns
            Active polls whose end timestamp is reached.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            SELECT * FROM polls
            WHERE status = 'active' AND ends_at <= ?
            ORDER BY ends_at ASC
            """,
            (now.isoformat(),),
        )
        rows = await cursor.fetchall()
        return [self._row_to_poll(row) for row in rows]

    async def finish_poll(self, poll_id: int, ended_at: datetime) -> None:
        """Mark a poll as ended and persist its completion timestamp.

        ## Parameters
            - poll_id: Poll identifier being finalized.
            - ended_at: Completion timestamp.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            """
            UPDATE polls
            SET status = 'ended', ended_at = ?
            WHERE id = ?
            """,
            (ended_at.isoformat(), poll_id),
        )
        await self.connection.commit()

    async def record_ban_action(
        self,
        guild_id: int,
        actor_id: int,
        target_id: int,
        created_at: datetime,
    ) -> None:
        """Store a moderation ban action for abuse-protection tracking.

        ## Parameters
            - guild_id: Guild identifier where the ban occurred.
            - actor_id: Moderator identifier executing the ban.
            - target_id: Member identifier who was banned.
            - created_at: Ban timestamp.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            """
            INSERT INTO ban_actions (guild_id, actor_id, target_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (guild_id, actor_id, target_id, created_at.isoformat()),
        )
        await self.connection.commit()

    async def count_ban_actions_since(self, guild_id: int, actor_id: int, since: datetime) -> int:
        """Count how many bans a moderator executed since a given timestamp.

        ## Parameters
            - guild_id: Guild identifier used to scope the query.
            - actor_id: Moderator identifier to aggregate.
            - since: Lower timestamp bound for the sliding window.

        ## Returns
            The number of recorded bans in the requested interval.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM ban_actions
            WHERE guild_id = ? AND actor_id = ? AND created_at >= ?
            """,
            (guild_id, actor_id, since.isoformat()),
        )
        row = await cursor.fetchone()
        return int(row["total"]) if row else 0

    async def has_social_post(self, platform: str, external_id: str) -> bool:
        """Check whether a social post was already announced previously.

        ## Parameters
            - platform: Social network source key.
            - external_id: Upstream content identifier.

        ## Returns
            True when the post was already announced.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT 1 FROM social_posts WHERE platform = ? AND external_id = ? LIMIT 1",
            (platform, external_id),
        )
        return await cursor.fetchone() is not None

    async def store_social_post(self, platform: str, external_id: str, published_at: datetime) -> None:
        """Persist a social post as already announced to avoid duplicates.

        ## Parameters
            - platform: Social network source key.
            - external_id: Upstream content identifier.
            - published_at: Post publication timestamp.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            """
            INSERT OR IGNORE INTO social_posts (platform, external_id, published_at)
            VALUES (?, ?, ?)
            """,
            (platform, external_id, published_at.isoformat()),
        )
        await self.connection.commit()

    async def get_cache_entry(self, key: str) -> dict[str, Any] | None:
        """Read a cached payload entry from the database by key.

        ## Parameters
            - key: Cache key to retrieve.

        ## Returns
            A payload dictionary containing data and updated_at metadata, or None.
        """

        assert self.connection is not None
        cursor = await self.connection.execute(
            "SELECT payload, updated_at FROM cache_entries WHERE key = ? LIMIT 1",
            (key,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "payload": json.loads(row["payload"]),
            "updated_at": row["updated_at"],
        }

    async def set_cache_entry(self, key: str, payload: dict[str, Any], updated_at: datetime) -> None:
        """Create or replace a cached payload entry in the database.

        ## Parameters
            - key: Cache key to create or replace.
            - payload: Serializable cache payload.
            - updated_at: Timestamp associated with the cached content.

        ## Returns
            None.
        """

        assert self.connection is not None
        await self.connection.execute(
            """
            INSERT INTO cache_entries (key, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key)
            DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (key, json.dumps(payload), updated_at.isoformat()),
        )
        await self.connection.commit()

    def _row_to_ticket(self, row: aiosqlite.Row) -> TicketRecord:
        return TicketRecord(
            id=int(row["id"]),
            guild_id=int(row["guild_id"]),
            channel_id=int(row["channel_id"]),
            author_id=int(row["author_id"]),
            category_key=row["category_key"],
            reason=row["reason"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            closed_at=datetime.fromisoformat(row["closed_at"]) if row["closed_at"] else None,
            closed_by_id=int(row["closed_by_id"]) if row["closed_by_id"] else None,
            transcript_path=row["transcript_path"],
        )

    def _row_to_giveaway(self, row: aiosqlite.Row) -> GiveawayRecord:
        return GiveawayRecord(
            id=int(row["id"]),
            guild_id=int(row["guild_id"]),
            channel_id=int(row["channel_id"]),
            message_id=int(row["message_id"]) if row["message_id"] else None,
            host_id=int(row["host_id"]),
            title=row["title"],
            description=row["description"],
            winner_count=int(row["winner_count"]),
            ends_at=datetime.fromisoformat(row["ends_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            status=row["status"],
            winner_ids=json.loads(row["winner_ids"]),
        )

    def _row_to_review(self, row: aiosqlite.Row) -> ReviewRecord:
        return ReviewRecord(
            id=int(row["id"]),
            guild_id=int(row["guild_id"]),
            author_id=int(row["author_id"]),
            author_name=row["author_name"],
            scripts=row["scripts"],
            rating=int(row["rating"]),
            comment=row["comment"],
            translated=row["translated"],
            created_at=datetime.fromisoformat(row["created_at"]),
            source_message_id=int(row["source_message_id"]) if row["source_message_id"] else None,
            posted_message_id=int(row["posted_message_id"]) if row["posted_message_id"] else None,
            content_cleaned=bool(row["content_cleaned"]) if "content_cleaned" in row.keys() else False,
        )

    def _row_to_poll(self, row: aiosqlite.Row) -> PollRecord:
        return PollRecord(
            id=int(row["id"]),
            guild_id=int(row["guild_id"]),
            channel_id=int(row["channel_id"]),
            message_id=int(row["message_id"]) if row["message_id"] else None,
            author_id=int(row["author_id"]),
            question=row["question"],
            description=row["description"],
            options=json.loads(row["options"]),
            ends_at=datetime.fromisoformat(row["ends_at"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            status=row["status"] if "status" in row.keys() else "active",
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
        )
