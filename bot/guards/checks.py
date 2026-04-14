from __future__ import annotations

from collections.abc import Callable

import discord
from discord import app_commands


def _get_interaction_member(interaction: discord.Interaction) -> discord.Member | None:
    member = interaction.user
    if isinstance(member, discord.Member):
        return member
    if interaction.guild is None:
        return None
    return interaction.guild.get_member(interaction.user.id)


def has_configured_role_permissions(interaction: discord.Interaction, role_ids: list[int]) -> bool:
    """Check whether the interaction user owns at least one configured role.

    ## Parameters
        - interaction: Interaction to evaluate.
        - role_ids: Configured role identifiers accepted for the action.

    ## Returns
        True when the invoking member owns one of the configured roles or has administrator.
    """

    member = _get_interaction_member(interaction)
    return bool(member is not None and (member.guild_permissions.administrator or any(role.id in role_ids for role in member.roles)))


def has_any_role(*role_ids: int) -> Callable[[discord.Interaction], bool]:
    """Build a reusable slash-command check that authorizes members owning at least one role.

    ## Parameters
        - role_ids: Discord role identifiers that authorize the interaction.

    ## Returns
        A reusable app_commands check predicate.
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        member = _get_interaction_member(interaction)
        if member is None:
            raise app_commands.CheckFailure("Member context is required.")
        if member.guild_permissions.administrator or any(role.id in role_ids for role in member.roles):
            return True
        raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")

    return app_commands.check(predicate)


def has_staff_permissions(interaction: discord.Interaction, staff_role_ids: list[int]) -> bool:
    """Check whether the interaction user owns the configured staff bot role.

    ## Parameters
        - interaction: Interaction to evaluate.
        - staff_role_ids: Central staff bot role identifiers.

    ## Returns
        True when the invoking member owns the configured role.
    """

    return has_configured_role_permissions(interaction, staff_role_ids)


def can_use_ban_commands(interaction: discord.Interaction, ban_role_ids: list[int], staff_role_ids: list[int]) -> bool:
    """Check whether the interaction user can access ban-related bot features.

    ## Parameters
        - interaction: Interaction to evaluate.
        - ban_role_ids: Roles required for ban commands.
        - staff_role_ids: Additional roles accepted as an override.

    ## Returns
        True when the member can execute moderation bans.
    """

    member = _get_interaction_member(interaction)
    if member is None:
        return False
    if member.guild_permissions.administrator:
        return True
    owned_roles = {role.id for role in member.roles}
    return bool(owned_roles.intersection(ban_role_ids) or owned_roles.intersection(staff_role_ids))
