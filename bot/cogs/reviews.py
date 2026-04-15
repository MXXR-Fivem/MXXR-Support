from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.guards.checks import has_staff_permissions

if TYPE_CHECKING:
    from bot.app import ShopBot


class ReviewsCog(commands.Cog):
    def __init__(self, bot: ShopBot) -> None:
        self.bot = bot

    @app_commands.command(name="review-panel", description="Publie le panneau d'avis")
    async def review_panel(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
        if interaction.guild is None:
            raise app_commands.CheckFailure("Cette commande doit être utilisée dans le serveur.")

        await interaction.response.defer(ephemeral=True)
        published = await container.reviews.publish_review_panel(interaction.guild)
        if not published:
            raise app_commands.AppCommandError("Le bot n'a pas pu publier le panel d'avis dans le salon configuré.")
        await interaction.followup.send(
            embed=container.embeds.success("Panneau publié", "Le panneau d'avis a été publié dans le salon d'avis."),
            ephemeral=True,
        )

    @app_commands.command(name="review-import-channel", description="Importe les anciens avis depuis un salon Discord")
    async def review_import_channel(
        self,
        interaction: discord.Interaction,
        source_channel: discord.TextChannel,
        repost: bool = True,
        limit: app_commands.Range[int, 1, 1000] | None = None,
    ) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")

        await interaction.response.defer(ephemeral=True)
        if interaction.guild is None:
            raise app_commands.CheckFailure("Cette commande doit être utilisée dans le serveur.")

        me = interaction.guild.me
        if me is None:
            raise app_commands.AppCommandError("Impossible de vérifier les permissions du bot sur le salon source.")
        source_permissions = source_channel.permissions_for(me)
        if not source_permissions.view_channel or not source_permissions.read_message_history:
            await interaction.followup.send(
                embed=container.embeds.error(
                    "Accès refusé au salon source",
                    "Le bot doit pouvoir voir le salon source et lire son historique pour importer les avis.",
                ),
                ephemeral=True,
            )
            return

        scanned = 0
        imported = 0
        posted = 0
        skipped = 0

        try:
            async for message in source_channel.history(limit=limit, oldest_first=True):
                scanned += 1
                review = await container.reviews.import_review_message(message)
                if review is None:
                    skipped += 1
                    continue
                imported += 1
                if repost:
                    embed = container.reviews.build_review_embed(review)
                    if await container.reviews.send_review_embed(
                        interaction.guild,
                        embed,
                        refresh_panel=False,
                        review=review,
                    ):
                        posted += 1
        except discord.Forbidden:
            await interaction.followup.send(
                embed=container.embeds.error(
                    "Import impossible",
                    "Le bot n'a pas accès à l'historique de ce salon source. Vérifie `Voir le salon` et `Lire l'historique des messages`.",
                ),
                ephemeral=True,
            )
            return

        if repost and posted > 0:
            await container.reviews.publish_review_panel(interaction.guild)

        summary = (
            f"Salon source: {source_channel.mention}\n"
            f"Messages lus: `{scanned}`\n"
            f"Avis importés: `{imported}`\n"
            f"Avis repostés: `{posted}`\n"
            f"Messages ignorés: `{skipped}`"
        )
        await interaction.followup.send(
            embed=container.embeds.success("Import des avis terminé", summary),
            ephemeral=True,
        )

    @app_commands.command(
        name="review-translate-backfill",
        description="Traduit en anglais un lot d'avis déjà présents en base",
    )
    async def review_translate_backfill(
        self,
        interaction: discord.Interaction,
        batch_size: app_commands.Range[int, 1, 100] = 20,
    ) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")

        await interaction.response.defer(ephemeral=True)
        try:
            processed, translated, remaining = await container.reviews.backfill_missing_translations(batch_size)
        except RuntimeError as error:
            await interaction.followup.send(
                embed=container.embeds.error("Traduction indisponible", str(error)),
                ephemeral=True,
            )
            return

        summary = (
            f"Avis traités: `{processed}`\n"
            f"Avis traduits: `{translated}`\n"
            f"Avis restants: `{remaining}`"
        )
        await interaction.followup.send(
            embed=container.embeds.success("Backfill des traductions terminé", summary),
            ephemeral=True,
        )

    @app_commands.command(
        name="review-clean-backfill",
        description="Nettoie en base un lot d'avis déjà présents",
    )
    async def review_clean_backfill(
        self,
        interaction: discord.Interaction,
        batch_size: app_commands.Range[int, 1, 500] = 100,
    ) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")

        await interaction.response.defer(ephemeral=True)
        processed, cleaned, remaining = await container.reviews.backfill_clean_reviews(batch_size)
        summary = (
            f"Avis traités: `{processed}`\n"
            f"Avis nettoyés: `{cleaned}`\n"
            f"Avis restants: `{remaining}`"
        )
        await interaction.followup.send(
            embed=container.embeds.success("Nettoyage des avis terminé", summary),
            ephemeral=True,
        )

    @app_commands.command(name="review-delete", description="Supprime un avis via son ID en base")
    async def review_delete(
        self,
        interaction: discord.Interaction,
        review_id: app_commands.Range[int, 1, 999999999],
    ) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
        if interaction.guild is None:
            raise app_commands.CheckFailure("Cette commande doit être utilisée dans le serveur.")

        await interaction.response.defer(ephemeral=True)
        deleted, message = await container.reviews.delete_review_by_id(interaction.guild, int(review_id))
        factory = container.embeds.success if deleted else container.embeds.error
        title = "Avis supprimé" if deleted else "Suppression impossible"
        await interaction.followup.send(
            embed=factory(title, message),
            ephemeral=True,
        )
