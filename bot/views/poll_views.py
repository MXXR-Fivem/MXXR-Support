from __future__ import annotations

import discord

from bot.utils.time import utcnow
from bot.views.ticket_views import get_bot


class PollVoteView(discord.ui.View):
    def __init__(self, option_count: int) -> None:
        super().__init__(timeout=None)
        for index in range(option_count):
            self.add_item(PollVoteButton(index))


class PollVoteButton(discord.ui.Button["PollVoteView"]):
    def __init__(self, option_index: int) -> None:
        super().__init__(
            label=f"Option {option_index + 1}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"poll:vote:{option_index}",
        )
        self.option_index = option_index

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = get_bot(interaction)
        container = bot.container
        assert container is not None
        if interaction.message is None:
            raise RuntimeError("Poll message is unavailable.")
        poll = await container.database.get_poll_by_message(interaction.message.id)
        if poll is None:
            embed = container.embeds.error("Sondage introuvable", "Ce sondage n'existe plus.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if poll.status != "active" or utcnow() >= poll.ends_at:
            embed = container.embeds.warning("Sondage terminé", "Ce sondage n'accepte plus de votes.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if self.option_index >= len(poll.options):
            embed = container.embeds.error("Option invalide", "Cette option n'est pas disponible.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await container.polls.register_vote(int(poll.id), interaction.user.id, self.option_index)
        results = await container.polls.get_results(int(poll.id))
        embed = container.polls.build_poll_embed(poll, results)
        await interaction.message.edit(embed=embed, view=PollVoteView(option_count=len(poll.options)))
        await interaction.response.send_message(
            embed=container.embeds.success("Vote enregistré", "Votre vote a été pris en compte."),
            ephemeral=True,
        )
