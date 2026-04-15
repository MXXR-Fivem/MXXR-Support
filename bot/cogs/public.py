from __future__ import annotations

from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.public.avatar import build_avatar_embed
from bot.commands.public.debug_perms import build_debug_perms_embed
from bot.commands.public.help import build_help_embed
from bot.commands.public.info import build_info_embed
from bot.commands.public.ping import build_ping_embed
from bot.commands.staff.announcements import (
    build_script_info_embed,
    build_script_update_embed,
    build_tebex_info_embed,
)
from bot.commands.staff.help import build_staff_help_embed
from bot.commands.staff.social import PLATFORM_LABELS, SocialPlatform, build_social_post_embed
from bot.guards.checks import has_staff_permissions
from bot.utils.time import utcnow

if TYPE_CHECKING:
    from bot.app import ShopBot


class PublicCog(commands.Cog):
    def __init__(self, bot: ShopBot) -> None:
        self.bot = bot

    @staticmethod
    def _is_http_url(value: str) -> bool:
        return value.startswith("http://") or value.startswith("https://")

    @staticmethod
    def _resolve_target_channel(
        interaction: discord.Interaction,
        channel: discord.TextChannel | None,
    ) -> discord.TextChannel:
        target_channel = channel
        if target_channel is None and isinstance(interaction.channel, discord.TextChannel):
            target_channel = interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            raise app_commands.AppCommandError("Le salon cible est introuvable ou n'est pas textuel.")
        return target_channel

    @app_commands.command(name="help", description="Affiche les commandes principales du bot")
    async def help_command(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        await interaction.response.send_message(embed=build_help_embed(container, interaction), ephemeral=True)

    @app_commands.command(name="help-admin", description="Affiche les commandes réservées au staff")
    async def help_admin_command(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
        await interaction.response.send_message(embed=build_staff_help_embed(container), ephemeral=True)

    @app_commands.command(name="info", description="Affiche les informations de la boutique")
    async def info_command(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        await interaction.response.send_message(embed=await build_info_embed(container), ephemeral=True)

    @app_commands.command(name="avatar", description="Affiche l'avatar d'un membre")
    async def avatar_command(self, interaction: discord.Interaction, member: discord.User | None = None) -> None:
        container = self.bot.container
        assert container is not None
        target = member or interaction.user
        await interaction.response.send_message(embed=build_avatar_embed(container, target), ephemeral=True)

    @app_commands.command(name="ping", description="Affiche la latence du bot")
    async def ping_command(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(embed=build_ping_embed(container, latency_ms), ephemeral=True)

    @app_commands.command(name="debug-perms", description="Affiche les rôles détectés et configurés pour le bot")
    async def debug_permissions_command(self, interaction: discord.Interaction) -> None:
        container = self.bot.container
        assert container is not None
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            raise app_commands.CheckFailure("Cette commande doit être utilisée dans le serveur.")
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
        await interaction.response.send_message(
            embed=build_debug_perms_embed(container, interaction.user),
            ephemeral=True,
        )

    @app_commands.command(name="social-post", description="Publie manuellement un post réseau dans le salon news")
    @app_commands.describe(
        platform="Plateforme concernée",
        title="Titre affiché dans l'embed",
        url="Lien du contenu",
        summary="Résumé optionnel du contenu",
        channel="Salon cible, sinon le salon news configuré",
    )
    @app_commands.choices(
        platform=[
            app_commands.Choice(name=label, value=value)
            for value, label in PLATFORM_LABELS.items()
        ]
    )
    async def social_post_command(
        self,
        interaction: discord.Interaction,
        platform: app_commands.Choice[str],
        title: app_commands.Range[str, 1, 256],
        url: app_commands.Range[str, 1, 1000],
        summary: app_commands.Range[str, 1, 4000] | None = None,
        channel: discord.TextChannel | None = None,
    ) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
        if interaction.guild is None:
            raise app_commands.CheckFailure("Cette commande doit être utilisée dans le serveur.")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise app_commands.AppCommandError("Le lien doit commencer par `http://` ou `https://`.")

        target_channel = channel or interaction.guild.get_channel(container.config.channels.news)
        if not isinstance(target_channel, discord.TextChannel):
            raise app_commands.AppCommandError("Le salon news configuré est introuvable ou n'est pas textuel.")

        selected_platform = platform.value
        if selected_platform not in PLATFORM_LABELS:
            raise app_commands.AppCommandError("Plateforme invalide.")

        platform_key = cast(SocialPlatform, selected_platform)
        published_at = utcnow()
        embed = build_social_post_embed(
            container=container,
            platform=platform_key,
            title=title,
            url=url,
            summary=summary,
            published_at=published_at,
        )
        await target_channel.send(embed=embed)
        await container.database.store_social_post(platform_key, url, published_at)
        await interaction.response.send_message(
            embed=container.embeds.success(
                "Post publié",
                f"Le post {PLATFORM_LABELS[platform_key]} a été publié dans {target_channel.mention}.",
            ),
            ephemeral=True,
        )

    @app_commands.command(name="tebex-info", description="Publie les instructions Tebex dans un salon")
    @app_commands.describe(channel="Salon cible, sinon le salon actuel")
    async def tebex_info_command(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
        if interaction.guild is None:
            raise app_commands.CheckFailure("Cette commande doit être utilisée dans le serveur.")

        target_channel = self._resolve_target_channel(interaction, channel)
        await target_channel.send(
            content="@everyone",
            embed=build_tebex_info_embed(container),
            allowed_mentions=discord.AllowedMentions(everyone=True),
        )
        await interaction.response.send_message(
            embed=container.embeds.success(
                "Informations Tebex publiées",
                f"L'embed Tebex a été envoyé dans {target_channel.mention}.",
            ),
            ephemeral=True,
        )

    @app_commands.command(name="script-info", description="Publie la fiche d'information d'un script")
    @app_commands.describe(
        title="Titre affiché dans l'embed",
        video_url="Lien de la vidéo de présentation",
        tebex_url="Lien Tebex du script",
        doc_url="Lien de documentation optionnel",
        channel="Salon cible, sinon le salon actuel",
    )
    async def script_info_command(
        self,
        interaction: discord.Interaction,
        title: app_commands.Range[str, 1, 256],
        video_url: app_commands.Range[str, 1, 1000],
        tebex_url: app_commands.Range[str, 1, 1000],
        doc_url: app_commands.Range[str, 1, 1000] | None = None,
        channel: discord.TextChannel | None = None,
    ) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
        if interaction.guild is None:
            raise app_commands.CheckFailure("Cette commande doit être utilisée dans le serveur.")
        if not self._is_http_url(video_url):
            raise app_commands.AppCommandError("Le lien vidéo doit commencer par `http://` ou `https://`.")
        if not self._is_http_url(tebex_url):
            raise app_commands.AppCommandError("Le lien Tebex doit commencer par `http://` ou `https://`.")
        if doc_url is not None and not self._is_http_url(doc_url):
            raise app_commands.AppCommandError("Le lien de documentation doit commencer par `http://` ou `https://`.")

        target_channel = self._resolve_target_channel(interaction, channel)
        await target_channel.send(embed=build_script_info_embed(container, title, video_url, tebex_url, doc_url))
        await interaction.response.send_message(
            embed=container.embeds.success(
                "Fiche script publiée",
                f"L'embed du script a été envoyé dans {target_channel.mention}.",
            ),
            ephemeral=True,
        )

    @app_commands.command(name="script-update", description="Publie un embed de nouveautes pour un script")
    @app_commands.describe(
        title="Titre de la mise a jour",
        updates="Texte des nouveautes ou changements",
        video_url="Lien video optionnel de la mise a jour",
        channel="Salon cible, sinon le salon actuel",
    )
    async def script_update_command(
        self,
        interaction: discord.Interaction,
        title: app_commands.Range[str, 1, 256],
        updates: app_commands.Range[str, 1, 4000],
        video_url: app_commands.Range[str, 1, 1000] | None = None,
        channel: discord.TextChannel | None = None,
    ) -> None:
        container = self.bot.container
        assert container is not None
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
        if interaction.guild is None:
            raise app_commands.CheckFailure("Cette commande doit être utilisée dans le serveur.")
        if video_url is not None and not self._is_http_url(video_url):
            raise app_commands.AppCommandError("Le lien video doit commencer par `http://` ou `https://`.")

        target_channel = self._resolve_target_channel(interaction, channel)
        await target_channel.send(embed=build_script_update_embed(container, title, updates, video_url))
        await interaction.response.send_message(
            embed=container.embeds.success(
                "Mise a jour publiee",
                f"L'embed de mise a jour a ete envoye dans {target_channel.mention}.",
            ),
            ephemeral=True,
        )
