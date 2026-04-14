from __future__ import annotations

import discord

from bot.embeds.factory import EmbedFactory
from bot.models.domain import PollRecord
from bot.storage.database import Database
from bot.utils.time import format_datetime, utcnow


class PollService:
    def __init__(self, database: Database, embed_factory: EmbedFactory) -> None:
        self.database = database
        self.embed_factory = embed_factory

    async def create_poll(self, poll: PollRecord) -> int:
        """Persist a newly created poll before it is published to Discord.

        ## Parameters
            - poll: Poll payload to persist.

        ## Returns
            The created poll identifier.
        """

        poll.id = await self.database.create_poll(poll)
        return int(poll.id)

    async def register_vote(self, poll_id: int, user_id: int, option_index: int) -> None:
        """Store or update a member vote for a poll.

        ## Parameters
            - poll_id: Poll identifier receiving the vote.
            - user_id: Member identifier casting the vote.
            - option_index: Selected option index.

        ## Returns
            None.
        """

        await self.database.upsert_poll_vote(poll_id, user_id, option_index, utcnow())

    async def get_results(self, poll_id: int) -> dict[int, int]:
        """Return the current aggregated vote totals for a poll.

        ## Parameters
            - poll_id: Poll identifier to aggregate.

        ## Returns
            A mapping of option index to vote count.
        """

        return await self.database.get_poll_results(poll_id)

    async def finalize_poll(self, poll: PollRecord) -> dict[int, int]:
        """Finalize a poll and return its aggregated results.

        ## Parameters
            - poll: Poll record to finalize.

        ## Returns
            Aggregated vote totals for the poll.
        """

        results = await self.database.get_poll_results(int(poll.id))
        await self.database.finish_poll(int(poll.id), utcnow())
        return results

    def build_poll_embed(self, poll: PollRecord, results: dict[int, int] | None = None) -> discord.Embed:
        """Build the branded embed representing a poll and its current results.

        ## Parameters
            - poll: Poll record to render.
            - results: Optional vote totals per option.

        ## Returns
            A branded poll embed.
        """

        embed = self.embed_factory.poll(poll.question, poll.description)
        lines: list[str] = []
        results = results or {}
        for index, option in enumerate(poll.options):
            total = results.get(index, 0)
            lines.append(f"`{index + 1}` {option} • **{total}** vote(s)")
        embed.add_field(name="Options", value="\n".join(lines), inline=False)
        embed.add_field(name="Fin", value=format_datetime(poll.ends_at), inline=True)
        if poll.status == "ended":
            embed.add_field(name="Statut", value="Terminé", inline=True)
        return embed

    def build_results_embed(self, poll: PollRecord, results: dict[int, int]) -> discord.Embed:
        """Build the branded embed shown when a poll ends.

        ## Parameters
            - poll: Poll record that ended.
            - results: Final vote totals.

        ## Returns
            A branded poll results embed.
        """

        ended_poll = poll.model_copy(update={"status": "ended", "ended_at": utcnow()})
        embed = self.build_poll_embed(ended_poll, results)
        winners = self.get_winner_indices(poll, results)
        if not results:
            summary = "Aucun vote enregistré."
        elif len(winners) == 1:
            summary = f"Gagnant: `{poll.options[winners[0]]}`"
        else:
            winner_labels = ", ".join(f"`{poll.options[index]}`" for index in winners)
            summary = f"Égalité: {winner_labels}"
        embed.add_field(name="Résultat", value=summary, inline=False)
        return embed

    def get_winner_indices(self, poll: PollRecord, results: dict[int, int]) -> list[int]:
        """Return the winning option indexes for a poll.

        ## Parameters
            - poll: Poll record to evaluate.
            - results: Final vote totals.

        ## Returns
            The list of winning option indexes, or an empty list if there are no votes.
        """

        non_zero_results = {index: total for index, total in results.items() if total > 0 and index < len(poll.options)}
        if not non_zero_results:
            return []
        max_votes = max(non_zero_results.values())
        return [index for index, total in non_zero_results.items() if total == max_votes]

    def build_winner_announcement(self, poll: PollRecord, results: dict[int, int]) -> str:
        """Build the message content announcing the winner of a poll.

        ## Parameters
            - poll: Poll record that ended.
            - results: Final vote totals.

        ## Returns
            A short human-readable announcement.
        """

        winners = self.get_winner_indices(poll, results)
        if not winners:
            return "📊 Le sondage est terminé. Aucun vote n'a été enregistré."
        if len(winners) == 1:
            return f"🏆 Le sondage est terminé. Option gagnante: **{poll.options[winners[0]]}**"
        winner_labels = ", ".join(f"**{poll.options[index]}**" for index in winners)
        return f"📊 Le sondage est terminé sur une égalité entre {winner_labels}"
