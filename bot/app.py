from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import discord
import httpx
from discord import app_commands
from discord.ext import commands

from bot.cogs.giveaways import GiveawaysCog
from bot.cogs.moderation import ModerationCog
from bot.cogs.polls import PollsCog
from bot.cogs.public import PublicCog
from bot.cogs.reviews import ReviewsCog
from bot.cogs.tickets import TicketsCog
from bot.config.settings import EnvironmentSettings, load_app_config, load_environment
from bot.config.models import AppConfig
from bot.embeds.factory import EmbedFactory
from bot.services.ban_protection_service import BanProtectionService
from bot.services.giveaway_service import GiveawayService
from bot.services.http import build_async_client
from bot.services.moderation_service import ModerationService
from bot.services.poll_service import PollService
from bot.services.review_service import ReviewService
from bot.services.review_api_service import ReviewApiService
from bot.services.tebex_client import TebexClient
from bot.services.tebex_service import TebexService
from bot.services.ticket_service import TicketService
from bot.storage.database import Database
from bot.tasks.giveaway_watch import GiveawayWatcherTask
from bot.tasks.poll_watch import PollWatcherTask
from bot.tasks.presence import PresenceTask
from bot.utils.logging import configure_logging
from bot.views.giveaway_views import GiveawayJoinView
from bot.views.poll_views import PollVoteView
from bot.views.review_views import ReviewPanelView
from bot.views.ticket_views import TicketCloseView, TicketPanelView

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BotContainer:
    settings: EnvironmentSettings
    config: AppConfig
    database: Database
    http_client: httpx.AsyncClient
    embeds: EmbedFactory
    tebex: TebexService
    tickets: TicketService
    giveaways: GiveawayService
    reviews: ReviewService
    review_api: ReviewApiService
    polls: PollService
    moderation: ModerationService
    ban_protection: BanProtectionService


class ShopBot(commands.Bot):
    def __init__(self) -> None:
        settings = load_environment()
        configure_logging(settings.log_level)
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.message_content = True
        intents.bans = True
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=settings.discord_client_id,
        )
        self.settings = settings
        self.container: BotContainer | None = None
        self.presence_task: PresenceTask | None = None
        self.giveaway_task: GiveawayWatcherTask | None = None
        self.poll_task: PollWatcherTask | None = None

    async def setup_hook(self) -> None:
        """Initialize services, register views and cogs, start background tasks, and sync slash commands.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        self.container = await self._build_container(self.settings)
        self.add_view(TicketPanelView())
        self.add_view(TicketCloseView())
        self.add_view(ReviewPanelView())
        self.add_view(GiveawayJoinView())
        self.add_view(PollVoteView(option_count=5))

        await self.add_cog(PublicCog(self))
        await self.add_cog(TicketsCog(self))
        await self.add_cog(ReviewsCog(self))
        await self.add_cog(GiveawaysCog(self))
        await self.add_cog(PollsCog(self))
        await self.add_cog(ModerationCog(self))

        self.tree.on_error = self.on_tree_error
        await self.container.review_api.start()
        self._start_background_tasks()
        await self._sync_commands()

    async def close(self) -> None:
        """Stop background tasks, close shared resources, and shut down the bot cleanly.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        for task_runner in (self.presence_task, self.giveaway_task, self.poll_task):
            if task_runner is not None:
                task_runner.stop()

        if self.container is not None:
            await self.container.review_api.stop()
            await self.container.http_client.aclose()
            await self.container.database.close()
        await super().close()

    async def on_ready(self) -> None:
        """Log that the bot is connected and ready to serve interactions.

        ## Parameters
            - None.

        ## Returns
            None.
        """

        logger.info("Bot ready as %s (%s)", self.user, self.user.id if self.user else "unknown")

    async def on_tree_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Handle slash-command errors and return a branded Discord error response.

        ## Parameters
            - interaction: Interaction that raised an application command error.
            - error: Application command exception instance.

        ## Returns
            None.
        """

        if self.container is None:
            return
        logger.exception("Application command failed", exc_info=error)
        if isinstance(error, app_commands.CheckFailure):
            embed = self.container.embeds.error("Accès refusé", str(error))
        else:
            embed = self.container.embeds.error(
                "Erreur",
                "Une erreur inattendue est survenue pendant l'exécution de la commande.",
            )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _build_container(self, settings: EnvironmentSettings) -> BotContainer:
        config = load_app_config(settings.config_path)
        if settings.bot_primary_color:
            config.branding.primary_color = settings.bot_primary_color
        config.environment = settings.environment

        settings.data_dir.mkdir(parents=True, exist_ok=True)
        database = Database(settings.database_path)
        await database.connect()
        http_client = build_async_client()
        embeds = EmbedFactory(config.branding)
        tebex_client = TebexClient(settings.tebex_base_url, settings.tebex_api_key, http_client) if settings.tebex_api_key else None
        tebex_service = TebexService(tebex_client, database)

        return BotContainer(
            settings=settings,
            config=config,
            database=database,
            http_client=http_client,
            embeds=embeds,
            tebex=tebex_service,
            tickets=TicketService(database, config, embeds),
            giveaways=GiveawayService(database, embeds),
            reviews=ReviewService(database, config, embeds, http_client, settings),
            review_api=ReviewApiService(settings, database),
            polls=PollService(database, embeds),
            moderation=ModerationService(config, embeds),
            ban_protection=BanProtectionService(database, config, embeds),
        )

    def _start_background_tasks(self) -> None:
        assert self.container is not None
        self.presence_task = PresenceTask(self, self.container)
        self.giveaway_task = GiveawayWatcherTask(self, self.container)
        self.poll_task = PollWatcherTask(self, self.container)
        self.presence_task.start()
        self.giveaway_task.start()
        self.poll_task.start()

    async def _sync_commands(self) -> None:
        assert self.container is not None
        guild_id = self.container.settings.discord_guild_id
        if guild_id:
            guild_object = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild_object)
            await self.tree.sync(guild=guild_object)
            logger.info("Synced commands to development guild %s", guild_id)
            # When developing with a fixed guild, remove leftover global commands
            # from older versions of the bot that used the same application token.
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            logger.info("Cleared global application commands while using development guild sync")
            return
        await self.tree.sync()
        logger.info("Synced global application commands")


def ensure_runtime_files() -> None:
    """Create the runtime data directory expected by the application.

    ## Parameters
        - None.

    ## Returns
        None.
    """

    Path("data").mkdir(parents=True, exist_ok=True)
