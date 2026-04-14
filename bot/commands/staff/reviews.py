from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


def build_review_panel_embed(container: BotContainer) -> discord.Embed:
    """Build the branded embed used for the public review submission panel.

    ## Parameters
        - container: Central application services and configuration container.

    ## Returns
        A branded embed inviting users to submit a review.
    """

    return container.embeds.review(
        "Avis clients",
        "Partagez votre retour sur les scripts achetés via le bouton ci-dessous. Réservé aux clients.",
    )
