from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


def build_staff_help_embed(container: BotContainer) -> discord.Embed:
    """Build the staff-only help embed listing restricted commands.

    ## Parameters
        - container: Central application services and configuration container.

    ## Returns
        A branded help embed for staff commands.
    """

    embed = container.embeds.info("Centre d'aide staff", "Liste des commandes réservées au staff.")
    staff_commands = [
        "`/help-admin` • Affiche l'aide staff",
        "`/ticket-panel` • Déploie le panneau de tickets",
        "`/social-post` • Publie manuellement un post réseau",
        "`/review-panel` • Déploie le panneau d'avis",
        "`/review-import-channel` • Importe les anciens avis d'un salon",
        "`/review-clean-backfill` • Nettoie un lot d'avis déjà en base",
        "`/review-translate-backfill` • Traduit un lot d'avis en anglais",
        "`/review-delete` • Supprime un avis via son ID en base",
        "`/giveaway-create` • Crée un giveaway",
        "`/giveaway-reroll` • Relance un tirage",
        "`/poll-create` • Crée un sondage",
        "`/ban` • Bannis un membre via le bot",
        "`/clear` • Supprime plusieurs messages",
    ]
    embed.add_field(name="Commandes staff", value="\n".join(staff_commands), inline=False)
    return embed
