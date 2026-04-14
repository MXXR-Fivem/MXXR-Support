from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


def _format_role_mentions(role_ids: list[int]) -> str:
    if not role_ids:
        return "Aucun"
    return " ".join(f"<@&{role_id}>" for role_id in role_ids)


def build_debug_perms_embed(container: BotContainer, member: discord.Member) -> discord.Embed:
    """Build a diagnostic embed showing the member roles and configured permission roles.

    ## Parameters
        - container: Central application services and configuration container.
        - member: Guild member requesting the diagnostic.

    ## Returns
        A branded informational embed with permission diagnostics.
    """

    member_role_ids = {role.id for role in member.roles}
    matched_staff_roles = [role_id for role_id in container.config.roles.staff_bot if role_id in member_role_ids]
    matched_ban_roles = [role_id for role_id in container.config.roles.ban_authorized if role_id in member_role_ids]

    embed = container.embeds.info("Diagnostic permissions", f"Vérification des rôles pour {member.mention}.")
    embed.add_field(
        name="Administrateur",
        value="Oui" if member.guild_permissions.administrator else "Non",
        inline=True,
    )
    embed.add_field(name="ID utilisateur", value=str(member.id), inline=True)
    embed.add_field(name="Rôles du membre", value=" ".join(role.mention for role in member.roles[1:]) or "Aucun", inline=False)
    embed.add_field(
        name="Rôles staff attendus",
        value=_format_role_mentions(container.config.roles.staff_bot),
        inline=False,
    )
    embed.add_field(
        name="Rôles staff détectés",
        value=_format_role_mentions(matched_staff_roles),
        inline=False,
    )
    embed.add_field(
        name="Rôles ban attendus",
        value=_format_role_mentions(container.config.roles.ban_authorized),
        inline=False,
    )
    embed.add_field(
        name="Rôles ban détectés",
        value=_format_role_mentions(matched_ban_roles),
        inline=False,
    )
    return embed
