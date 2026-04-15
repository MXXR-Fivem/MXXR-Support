from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config.settings import load_api_environment
from bot.services.review_api_service import ReviewApiService
from bot.storage.database import Database
from bot.utils.logging import configure_logging


async def main() -> None:
    """Launch the standalone review API process."""

    settings = load_api_environment()
    configure_logging(settings.log_level)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    database = Database(settings.database_path)
    await database.connect()
    review_api = ReviewApiService(settings, database)
    await review_api.start()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    try:
        await stop_event.wait()
    finally:
        await review_api.stop()
        await database.close()


if __name__ == "__main__":
    asyncio.run(main())
