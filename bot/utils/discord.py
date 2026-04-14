from __future__ import annotations

from typing import Iterable

import discord


def mention_roles(role_ids: Iterable[int]) -> str:
    """Convert a list of role IDs into a Discord mention string.

    ## Parameters
        - role_ids: Sequence of Discord role identifiers to format as mentions.

    ## Returns
        A space-separated mention string.
    """

    return " ".join(f"<@&{role_id}>" for role_id in role_ids)


def build_channel_overwrites(
    guild: discord.Guild,
    member: discord.Member,
    support_role_ids: Iterable[int],
) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
    """Build the permission overwrites required for a private ticket channel.

    ## Parameters
        - guild: Guild where the ticket channel will be created.
        - member: Member who should access the created private channel.
        - support_role_ids: Role identifiers that should also access the channel.

    ## Returns
        A dictionary of Discord permission overwrites.
    """

    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
    }
    if guild.me is not None:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            read_message_history=True,
        )
    for role_id in support_role_ids:
        role = guild.get_role(role_id)
        if role is not None:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
            )
    return overwrites
