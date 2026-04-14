from __future__ import annotations

import discord

from bot.views.ticket_views import get_bot


class GiveawayJoinView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    async def _get_active_giveaway(
        self,
        interaction: discord.Interaction,
    ) -> tuple["ShopBot", "BotContainer", discord.Message, object] | None:
        bot = get_bot(interaction)
        container = bot.container
        assert container is not None
        if interaction.message is None:
            raise RuntimeError("Giveaway message is unavailable.")
        giveaway = await container.database.get_giveaway_by_message(interaction.message.id)
        if giveaway is None or giveaway.status != "active":
            embed = container.embeds.error("Giveaway introuvable", "Ce giveaway n'est plus actif.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None
        return bot, container, interaction.message, giveaway

    async def _refresh_message(self, container: "BotContainer", message: discord.Message, giveaway: object) -> None:
        participant_count = await container.database.count_giveaway_entries(int(giveaway.id))
        await message.edit(
            embed=container.giveaways.build_giveaway_embed(giveaway, participant_count=participant_count),
            view=GiveawayJoinView(),
        )

    @discord.ui.button(
        label="Participer",
        style=discord.ButtonStyle.success,
        emoji="🎉",
        custom_id="giveaway:join",
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        resolved = await self._get_active_giveaway(interaction)
        if resolved is None:
            return
        _, container, message, giveaway = resolved

        created = await container.giveaways.register_participation(int(giveaway.id), interaction.user.id)
        if created:
            embed = container.embeds.success("Participation enregistrée", "Vous participez maintenant au giveaway.")
        else:
            embed = container.embeds.warning("Déjà inscrit", "Vous participez déjà à ce giveaway.")
        await self._refresh_message(container, message, giveaway)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Se désinscrire",
        style=discord.ButtonStyle.secondary,
        emoji="❌",
        custom_id="giveaway:leave",
    )
    async def leave_button(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        resolved = await self._get_active_giveaway(interaction)
        if resolved is None:
            return
        _, container, message, giveaway = resolved

        removed = await container.giveaways.unregister_participation(int(giveaway.id), interaction.user.id)
        if removed:
            embed = container.embeds.success("Participation retirée", "Vous ne participez plus au giveaway.")
        else:
            embed = container.embeds.warning("Aucune participation", "Vous n'étiez pas inscrit à ce giveaway.")
        await self._refresh_message(container, message, giveaway)
        await interaction.response.send_message(embed=embed, ephemeral=True)
