from __future__ import annotations

import logging
import random

import discord

from bot.embeds.factory import EmbedFactory
from bot.models.domain import GiveawayRecord
from bot.storage.database import Database
from bot.utils.time import format_datetime, utcnow

logger = logging.getLogger(__name__)


class GiveawayService:
    def __init__(self, database: Database, embed_factory: EmbedFactory) -> None:
        self.database = database
        self.embed_factory = embed_factory

    async def create_giveaway(self, giveaway: GiveawayRecord) -> int:
        """Persist a newly created giveaway before it is published to Discord.

        ## Parameters
            - giveaway: Giveaway definition to persist before publication.

        ## Returns
            The database identifier of the giveaway.
        """

        giveaway.id = await self.database.create_giveaway(giveaway)
        return int(giveaway.id)

    async def register_participation(self, giveaway_id: int, user_id: int) -> bool:
        """Register a member participation for a giveaway if they are not already entered.

        ## Parameters
            - giveaway_id: Giveaway identifier receiving the participation.
            - user_id: Member identifier joining the giveaway.

        ## Returns
            True when the user has been added, otherwise False if already registered.
        """

        return await self.database.add_giveaway_entry(giveaway_id, user_id, utcnow())

    async def unregister_participation(self, giveaway_id: int, user_id: int) -> bool:
        """Remove a member participation from a giveaway.

        ## Parameters
            - giveaway_id: Giveaway identifier from which the member leaves.
            - user_id: Member identifier leaving the giveaway.

        ## Returns
            True when the member was removed, otherwise False.
        """

        return await self.database.remove_giveaway_entry(giveaway_id, user_id)

    async def finalize_giveaway(self, giveaway: GiveawayRecord) -> list[int]:
        """Finalize a giveaway and draw winners from the registered entrants.

        ## Parameters
            - giveaway: Giveaway record to finalize and draw from.

        ## Returns
            The list of selected winner user identifiers.
        """

        entrants = await self.database.get_giveaway_entries(int(giveaway.id))
        if not entrants:
            winners: list[int] = []
        else:
            winner_count = min(giveaway.winner_count, len(entrants))
            winners = random.sample(entrants, k=winner_count)

        await self.database.finish_giveaway(int(giveaway.id), utcnow(), winners)
        logger.info("Ended giveaway %s with winners=%s", giveaway.id, winners)
        return winners

    async def reroll_giveaway(self, giveaway: GiveawayRecord) -> list[int]:
        """Draw replacement winners for a finished giveaway without repeating previous winners.

        ## Parameters
            - giveaway: Existing giveaway record for which a new draw is requested.

        ## Returns
            A fresh list of winner user identifiers.
        """

        entrants = await self.database.get_giveaway_entries(int(giveaway.id))
        remaining = [entrant for entrant in entrants if entrant not in giveaway.winner_ids]
        if not remaining:
            return []
        winner_count = min(giveaway.winner_count, len(remaining))
        return random.sample(remaining, k=winner_count)

    def build_giveaway_embed(self, giveaway: GiveawayRecord, participant_count: int = 0) -> discord.Embed:
        """Build the branded embed shown while a giveaway is active.

        ## Parameters
            - giveaway: Giveaway record to render into an embed.
            - participant_count: Current number of registered participants.

        ## Returns
            A branded giveaway embed.
        """

        embed = self.embed_factory.giveaway(giveaway.title, giveaway.description)
        self.embed_factory.add_fields(
            embed,
            (
                ("Gagnants", str(giveaway.winner_count), True),
                ("Participants", str(participant_count), True),
                ("Fin", format_datetime(giveaway.ends_at), True),
                ("Hébergé par", f"<@{giveaway.host_id}>", True),
            ),
        )
        return embed

    def build_results_embed(self, giveaway: GiveawayRecord, winners: list[int], participant_count: int | None = None) -> discord.Embed:
        """Build the branded embed announcing the final giveaway results.

        ## Parameters
            - giveaway: Giveaway record that has ended.
            - winners: Selected user identifiers.
            - participant_count: Optional total number of registered participants.

        ## Returns
            A branded embed summarizing the giveaway result.
        """

        if winners:
            description = "Les gagnants ont été tirés au sort automatiquement."
            winners_value = "\n".join(f"<@{winner}>" for winner in winners)
        else:
            description = "Personne n'a participé à ce giveaway."
            winners_value = "Aucun participant"

        embed = self.embed_factory.giveaway(f"{giveaway.title} • Terminé", description)
        fields: list[tuple[str, str, bool]] = [("Gagnants", winners_value, False)]
        if participant_count is not None:
            fields.append(("Participants", str(participant_count), True))
        fields.append(("Clôturé le", format_datetime(utcnow()), True))
        self.embed_factory.add_fields(embed, fields)
        return embed
