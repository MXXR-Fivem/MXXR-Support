from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.app import ShopBot, ensure_runtime_files


async def main() -> None:
    """Launch the Discord bot entrypoint inside the asyncio runtime.

    ## Parameters
        - None.

    ## Returns
        None.
    """

    ensure_runtime_files()
    bot = ShopBot()
    async with bot:
        await bot.start(bot.settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
