from __future__ import annotations

from datetime import timedelta

from bot.models.domain import GiveawayRecord
from bot.utils.time import utcnow


def build_giveaway_record(
    guild_id: int,
    channel_id: int,
    host_id: int,
    title: str,
    description: str,
    duration: timedelta,
    winner_count: int,
) -> GiveawayRecord:
    """Create a populated giveaway record from slash-command input values.

    ## Parameters
        - guild_id: Guild identifier hosting the giveaway.
        - channel_id: Channel identifier where the giveaway will be sent.
        - host_id: Staff identifier creating the giveaway.
        - title: Giveaway title.
        - description: Giveaway description.
        - duration: Giveaway duration before automatic closing.
        - winner_count: Number of winners to select.

    ## Returns
        A populated GiveawayRecord ready for persistence.
    """

    return GiveawayRecord(
        guild_id=guild_id,
        channel_id=channel_id,
        host_id=host_id,
        title=title,
        description=description,
        winner_count=winner_count,
        ends_at=utcnow() + duration,
    )
