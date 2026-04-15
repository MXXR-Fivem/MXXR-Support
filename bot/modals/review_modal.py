from __future__ import annotations

from typing import TYPE_CHECKING

import discord
import httpx

from bot.guards.checks import has_configured_role_permissions
from bot.models.domain import ReviewRecord
from bot.utils.time import utcnow

if TYPE_CHECKING:
    from bot.app import BotContainer


class ReviewModal(discord.ui.Modal, title="Laisser un avis"):
    scripts = discord.ui.TextInput(
        label="Scripts achetés",
        placeholder="Ex: MXXR_Garage, MXXR_Society",
        max_length=200,
    )
    rating = discord.ui.TextInput(
        label="Note",
        placeholder="Nombre entre 1 et 5",
        max_length=1,
    )
    comment = discord.ui.TextInput(
        label="Commentaire",
        style=discord.TextStyle.paragraph,
        placeholder="Décrivez votre expérience",
        max_length=1000,
    )

    def __init__(self, container: BotContainer) -> None:
        super().__init__()
        self.container = container

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Validate the submitted review modal, persist the review, and publish it to the configured channel.

        ## Parameters
            - interaction: Interaction submitted from the review modal.

        ## Returns
            None.
        """

        if interaction.guild is None:
            raise RuntimeError("Guild context is required.")
        allowed_roles = list({*self.container.config.roles.customer, *self.container.config.roles.staff_bot})
        if not has_configured_role_permissions(interaction, allowed_roles):
            embed = self.container.embeds.error(
                "Accès refusé",
                "Seuls les membres avec le rôle customer peuvent laisser un avis.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            rating_value = int(self.rating.value)
        except ValueError:
            embed = self.container.embeds.error("Note invalide", "La note doit être un nombre entre 1 et 5.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if rating_value < 1 or rating_value > 5:
            embed = self.container.embeds.error("Note invalide", "La note doit être comprise entre 1 et 5.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        review = ReviewRecord(
            guild_id=interaction.guild.id,
            author_id=interaction.user.id,
            author_name=interaction.user.display_name,
            scripts=self.scripts.value,
            rating=rating_value,
            comment=self.comment.value,
            created_at=utcnow(),
        )
        await self.container.reviews.save_review(review)
        try:
            await self.container.reviews.translate_review(review)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, RuntimeError):
            pass
        embed = self.container.reviews.build_review_embed(review)
        published = await self.container.reviews.send_review_embed(interaction.guild, embed, review=review)

        if published:
            response_embed = self.container.embeds.success("Avis envoyé", "Merci pour votre retour.")
        else:
            response_embed = self.container.embeds.warning(
                "Avis enregistré",
                "Votre avis a bien été enregistré, mais le bot n'a pas accès au salon d'avis configuré.",
            )
        await interaction.response.send_message(embed=response_embed, ephemeral=True)
