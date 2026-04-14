from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


def build_avatar_embed(container: BotContainer, user: discord.abc.User) -> discord.Embed:
    """Build the avatar embed for a Discord user.

    ## Parameters
        - container: Central application services and configuration container.
        - user: User whose avatar should be displayed.

    ## Returns
        A branded informational embed containing the user's avatar.
    """

    embed = container.embeds.info(
        "Avatar",
        f"Avatar de {user.mention if isinstance(user, (discord.Member, discord.User)) else user.display_name}.",
    )
    embed.set_image(url=user.display_avatar.url)
    embed.add_field(name="Lien direct", value=f"[Ouvrir l'avatar]({user.display_avatar.url})", inline=False)
    return embed
