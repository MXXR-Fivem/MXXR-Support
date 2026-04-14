from __future__ import annotations

import logging

from bot.constants.defaults import DEFAULT_LOG_FORMAT


def configure_logging(level: str) -> None:
    """Configure the root Python logger for the bot process.

    ## Parameters
        - level: Desired root logging level for the application.

    ## Returns
        None.
    """

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=DEFAULT_LOG_FORMAT,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
