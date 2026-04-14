from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from bot.models.domain import PollRecord
from bot.utils.time import utcnow


def parse_poll_options(raw_options: Iterable[str | None], max_options: int) -> list[str]:
    """Parse and validate the list of poll options received from the slash command.

    ## Parameters
        - raw_options: Iterable of raw option values coming from the slash command.
        - max_options: Maximum allowed number of options.

    ## Returns
        A validated list of poll options.
    """

    options = [item.strip() for item in raw_options if item and item.strip()]
    if len(options) < 2:
        raise ValueError("Un sondage doit contenir au moins 2 options.")
    if len(options) > max_options:
        raise ValueError(f"Un sondage ne peut pas dépasser {max_options} options.")
    return options


def build_poll_record(
    guild_id: int,
    channel_id: int,
    author_id: int,
    question: str,
    description: str,
    options: list[str],
    duration: timedelta,
) -> PollRecord:
    """Create a populated poll record from slash-command input values.

    ## Parameters
        - guild_id: Guild identifier hosting the poll.
        - channel_id: Channel identifier where the poll will be sent.
        - author_id: Staff identifier creating the poll.
        - question: Poll title or question.
        - description: Poll description.
        - options: Validated list of poll options.
        - duration: Poll duration.

    ## Returns
        A populated PollRecord ready for persistence.
    """

    return PollRecord(
        guild_id=guild_id,
        channel_id=channel_id,
        author_id=author_id,
        question=question,
        description=description,
        options=options,
        ends_at=utcnow() + duration,
        created_at=utcnow(),
    )
