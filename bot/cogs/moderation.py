from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.commands.staff.clear import build_clear_success_embed
from bot.commands.staff.moderation import build_ban_success_embed
from bot.guards.checks import can_use_ban_commands, has_staff_permissions

if TYPE_CHECKING:
    from bot.app import ShopBot


class ModerationCog(commands.Cog):
    def __init__(self, bot: ShopBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        container = self.bot.container
        assert container is not None
        if not container.moderation.should_delete_message(message):
            return
        await message.delete()
        logs_channel = message.guild.get_channel(container.config.channels.logs) if message.guild else None
        if isinstance(logs_channel, discord.TextChannel):
            await logs_channel.send(embed=container.moderation.build_log_embed(message))

    @app_commands.command(name="ban", description="Bannis un membre via le bot")
    async def ban_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
        delete_message_days: app_commands.Range[int, 0, 7] = 0,
    ) -> None:
        container = self.bot.container
        assert container is not None
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            raise RuntimeError("Guild member context is required.")
        if not can_use_ban_commands(
            interaction,
            container.config.roles.ban_authorized,
            container.config.roles.staff_bot,
        ):
            raise app_commands.CheckFailure("Vous n'avez pas le rôle autorisé pour bannir.")

        await interaction.guild.ban(
            member,
            reason=f"{reason} | via bot par {interaction.user} ({interaction.user.id})",
            delete_message_seconds=delete_message_days * 86400,
        )
        limit_exceeded, count = await container.ban_protection.record_ban_and_check_limit(
            interaction.guild,
            interaction.user,
            member.id,
        )
        await interaction.response.send_message(
            embed=build_ban_success_embed(container, member, reason),
            ephemeral=True,
        )
        if limit_exceeded:
            alert_channel_id = container.config.ban_protection.alert_channel_id or container.config.channels.logs
            alert_channel = interaction.guild.get_channel(alert_channel_id)
            if isinstance(alert_channel, discord.TextChannel):
                await alert_channel.send(embed=container.ban_protection.build_alert_embed(interaction.user, count))

    @app_commands.command(name="clear", description="Supprime plusieurs messages du salon")
    async def clear_messages(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
    ) -> None:
        container = self.bot.container
        assert container is not None
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            raise RuntimeError("Guild member context is required.")
        if not has_staff_permissions(interaction, container.config.roles.staff_bot):
            raise app_commands.CheckFailure("Vous n'avez pas la permission d'utiliser cette commande.")
        if not isinstance(interaction.channel, discord.TextChannel):
            raise app_commands.AppCommandError("La commande /clear doit être utilisée dans un salon textuel.")

        await interaction.response.defer(ephemeral=True)
        deleted_messages = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            embed=build_clear_success_embed(container, len(deleted_messages)),
            ephemeral=True,
        )
