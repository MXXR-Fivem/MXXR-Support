from __future__ import annotations

import discord

from bot.guards.checks import has_configured_role_permissions
from bot.modals.review_modal import ReviewModal
from bot.views.ticket_views import get_bot


class ReviewPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Laisser un avis",
        style=discord.ButtonStyle.success,
        emoji="⭐",
        custom_id="review:create",
    )
    async def review_button(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        bot = get_bot(interaction)
        assert bot.container is not None
        allowed_roles = list({*bot.container.config.roles.customer, *bot.container.config.roles.staff_bot})
        if not has_configured_role_permissions(interaction, allowed_roles):
            await interaction.response.send_message(
                embed=bot.container.embeds.error(
                    "Accès refusé",
                    "Seuls les membres avec le rôle customer peuvent laisser un avis.",
                ),
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(ReviewModal(bot.container))
