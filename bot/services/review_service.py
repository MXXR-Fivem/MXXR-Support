from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import discord
import httpx

from bot.config.settings import EnvironmentSettings
from bot.config.models import AppConfig
from bot.embeds.factory import EmbedFactory
from bot.models.domain import ReviewRecord
from bot.storage.database import Database
from bot.utils.time import format_datetime, utcnow
from bot.views.review_views import ReviewPanelView

logger = logging.getLogger(__name__)
REVIEW_PANEL_CACHE_KEY_PREFIX = "review_panel_message"


STAR_CHARS = {"★", "⭐", "🌟", "⭐️"}
DISCORD_ARTIFACT_PATTERNS = (
    (r"<@!?\d+>", ""),
    (r"<@&\d+>", ""),
    (r"<#\d+>", ""),
    (r"@(everyone|here)\b", ""),
)
SCRIPT_PREFIXES = (
    "script :",
    "scripts :",
    "script:",
    "scripts:",
    "ayant acheter le script:",
    "ayant acheter le script :",
    "ayant acheter les script:",
    "ayant acheter les script :",
)
LEGACY_REVIEW_HINTS = (
    "script",
    "scripts",
    "support",
    "service",
    "recommande",
    "achat",
    "achete",
    "acheté",
    "payer",
    "payé",
    "pris",
    "top",
    "parfait",
    "qualité",
    "rapide",
)
LEGACY_SCRIPT_PATTERNS = (
    r"achat du\s+([^\n.!]+)",
    r"achat de la\s+([^\n.!]+)",
    r"achat de l[ae']\s*([^\n.!]+)",
    r"catalogue\s+([^\n,.!]+)",
    r"\{\s*script\s+([^)\]}]+)",
    r"j[’']ai\s+(?:achete|acheté|payer|payé|pris)\s+(?:le|la|l[ae']|les)?\s*(?:script|job|catalogue)?\s*([^\n.!]+)",
    r"j[’']est\s+acheter\s+(?:le|la|l[ae']|les)?\s*(?:script|job|catalogue)?\s*([^\n.!]+)",
    r"script\s+(?!de\b)([a-z0-9+ \-_/]+)",
)


@dataclass(slots=True)
class ParsedReviewContent:
    scripts: str
    comment: str
    rating: int


def _normalize_review_text(raw_content: str) -> str:
    cleaned = raw_content.replace("\u2060", " ").replace("\ufeff", " ")
    return "\n".join(line.rstrip() for line in cleaned.splitlines()).strip()


def clean_review_text(raw_content: str) -> str:
    """Normalize review text by removing Discord-specific artifacts and leftover Markdown."""

    cleaned = _normalize_review_text(raw_content)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"<a?:[A-Za-z0-9_~\-]+:\d+>", "", cleaned)
    for pattern, replacement in DISCORD_ARTIFACT_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?<!\w)@[\w.\-]{2,32}", "", cleaned)
    cleaned = discord.utils.remove_markdown(cleaned)
    cleaned = cleaned.replace("`", "")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = "\n".join(line.strip(" \t") for line in cleaned.splitlines())
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _extract_rating(lines: list[str]) -> int | None:
    ratings: list[int] = []
    for line in lines:
        star_count = sum(line.count(char) for char in STAR_CHARS)
        if star_count:
            ratings.append(min(star_count, 5))

        textual_ratings = [min(int(match), 5) for match in re.findall(r"(\d+)\s*étoiles?", line, flags=re.IGNORECASE)]
        ratings.extend(textual_ratings)

        numeric_ratings = [int(match) for match in re.findall(r"([1-5])\s*/\s*5", line)]
        ratings.extend(numeric_ratings)

    return max(ratings) if ratings else None


def _clean_script_value(raw_value: str) -> str:
    cleaned = raw_value.strip(" :-_,.;()[]{}")
    cleaned = re.sub(r"<@!?\d+>", "", cleaned)
    cleaned = re.sub(r"@\S+", "", cleaned)
    cleaned = cleaned.replace("{", "").replace("}", "")
    cleaned = re.split(
        r"\b(?:et|mais|franchement|parfait|excellent|incroyable|au top|je recommande|support|service)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" :-_,.;()[]{}")
    return cleaned or "Non précisé"


def _extract_script_list_after_intro(lines: list[str]) -> str | None:
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "script" not in lowered:
            continue
        collected: list[str] = []
        for candidate in lines[index + 1 : index + 6]:
            stripped = candidate.strip(" -")
            if not stripped:
                continue
            if len(stripped.split()) <= 4 and ":" not in stripped and not stripped.endswith((".", "!", "?")):
                collected.append(stripped)
                continue
            break
        if collected:
            return ", ".join(collected)
    return None


def _extract_scripts(lines: list[str]) -> str:
    for line in lines:
        lowered = line.lower().strip()
        for prefix in SCRIPT_PREFIXES:
            if lowered.startswith(prefix):
                script_value = line.split(":", 1)[1].strip() if ":" in line else ""
                return script_value or "Non précisé"
        if lowered.startswith("script "):
            return line[7:].strip() or "Non précisé"

    inferred_list = _extract_script_list_after_intro(lines)
    if inferred_list is not None:
        return inferred_list

    normalized_text = " ".join(lines)
    for pattern in LEGACY_SCRIPT_PATTERNS:
        match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
        if match:
            return _clean_script_value(match.group(1))

    return "Non précisé"


def _looks_like_legacy_review(lines: list[str]) -> bool:
    normalized_text = " ".join(lines).lower()
    return any(keyword in normalized_text for keyword in LEGACY_REVIEW_HINTS)


def parse_legacy_review_content(raw_content: str) -> ParsedReviewContent | None:
    """Parse a legacy free-form review message into structured review fields.

    ## Parameters
        - raw_content: Raw legacy Discord message body.

    ## Returns
        Structured review fields, or None when the message is not parseable as a review.
    """

    normalized = _normalize_review_text(raw_content)
    if not normalized:
        return None

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    rating = _extract_rating(lines)
    if rating is None and _looks_like_legacy_review(lines):
        rating = 5
    if rating is None:
        return None

    scripts = _extract_scripts(lines)
    comment_lines: list[str] = []
    for line in lines:
        lowered = line.lower().strip()
        if any(lowered.startswith(prefix) for prefix in SCRIPT_PREFIXES) or lowered.startswith("script "):
            continue
        if lowered.startswith("note"):
            continue
        if lowered == "avis général :":
            continue
        if lowered.startswith("commentaire :"):
            comment_lines.append(line.split(":", 1)[1].strip())
            continue
        if "|" in line and re.search(r"\b[1-5]\s*/\s*5\b", line):
            continue
        if sum(line.count(char) for char in STAR_CHARS) >= 3 and len(line.replace(" ", "")) <= 20:
            continue
        comment_lines.append(line)

    comment = "\n".join(line for line in comment_lines if line).strip()
    if not comment:
        return None

    return ParsedReviewContent(scripts=scripts, comment=comment, rating=rating)


class ReviewService:
    def __init__(
        self,
        database: Database,
        config: AppConfig,
        embed_factory: EmbedFactory,
        http_client: httpx.AsyncClient,
        settings: EnvironmentSettings,
    ) -> None:
        self.database = database
        self.config = config
        self.embed_factory = embed_factory
        self.http_client = http_client
        self.deepl_api_base_url = settings.deepl_api_base_url.rstrip("/")
        self.deepl_api_key = settings.deepl_api_key
        self.translation_api_base_url = settings.translation_api_base_url.rstrip("/") if settings.translation_api_base_url else None
        self.translation_api_key = settings.translation_api_key
        self.translation_api_model = settings.translation_api_model

    async def save_review(self, review: ReviewRecord) -> int:
        """Persist a customer review in the storage layer.

        ## Parameters
            - review: Review payload to persist.

        ## Returns
            The created review identifier.
        """

        self.normalize_review_content(review)
        review.id = await self.database.save_review(review)
        return int(review.id)

    def build_review_embed(self, review: ReviewRecord) -> discord.Embed:
        """Render a branded review embed from a stored review record.

        ## Parameters
            - review: Review record to render.

        ## Returns
            A branded embed containing the customer feedback.
        """

        stars = "★" * review.rating + "☆" * (5 - review.rating)
        embed = self.embed_factory.review("Nouvel avis client", review.comment)
        client_value = f"{review.author_name} (<@{review.author_id}>)"
        self.embed_factory.add_fields(
            embed,
            (
                ("Client", client_value, True),
                ("Scripts", review.scripts, True),
                ("Note", stars, True),
                ("Envoyé le", format_datetime(review.created_at), True),
            ),
        )
        return embed

    def _review_panel_cache_key(self, guild_id: int) -> str:
        return f"{REVIEW_PANEL_CACHE_KEY_PREFIX}:{guild_id}"

    def normalize_review_content(self, review: ReviewRecord) -> None:
        """Clean the review text fields and mark the record as normalized."""

        review.comment = clean_review_text(review.comment)
        if review.translated:
            review.translated = clean_review_text(review.translated)
        review.content_cleaned = True

    def translation_enabled(self) -> bool:
        return bool(
            self.deepl_api_key
            or (self.translation_api_base_url and self.translation_api_key and self.translation_api_model)
        )

    async def import_review_message(self, message: discord.Message) -> ReviewRecord | None:
        """Parse, persist, and normalize a legacy review message.

        ## Parameters
            - message: Message from a legacy reviews channel.

        ## Returns
            The persisted review record, or None when the message should be skipped.
        """

        if message.author.bot:
            return None
        if await self.database.has_review_for_source_message(message.id):
            return None

        parsed_review = parse_legacy_review_content(message.content)
        if parsed_review is None:
            return None

        review = ReviewRecord(
            guild_id=message.guild.id if message.guild else 0,
            author_id=message.author.id,
            author_name=message.author.display_name,
            scripts=parsed_review.scripts,
            rating=parsed_review.rating,
            comment=parsed_review.comment,
            created_at=message.created_at,
            source_message_id=message.id,
        )
        await self.save_review(review)
        return review

    async def translate_review(self, review: ReviewRecord) -> str | None:
        """Translate a review comment to English and store it in the database.

        ## Parameters
            - review: Review record to translate.

        ## Returns
            The translated comment when available, otherwise None.
        """

        if not self.translation_enabled() or review.id is None:
            return None
        if review.translated:
            return review.translated

        translated = await self._translate_text_to_english(review.comment)
        review.translated = clean_review_text(translated)
        review.content_cleaned = True
        await self.database.update_review_translation(int(review.id), review.translated, content_cleaned=True)
        return review.translated

    async def backfill_missing_translations(self, batch_size: int) -> tuple[int, int, int]:
        """Translate a batch of stored reviews that are still missing English content.

        ## Parameters
            - batch_size: Maximum number of reviews to translate in this batch.

        ## Returns
            A tuple of processed, translated, and remaining review counts.
        """

        if not self.translation_enabled():
            raise RuntimeError("Translation API is not configured.")

        reviews = await self.database.get_reviews_missing_translation(batch_size)
        translated_count = 0
        for review in reviews:
            try:
                translated = await self.translate_review(review)
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
                logger.exception("Failed to translate review %s", review.id)
                continue
            if translated:
                translated_count += 1
        remaining = await self.database.count_reviews_missing_translation()
        return len(reviews), translated_count, remaining

    async def backfill_clean_reviews(self, batch_size: int) -> tuple[int, int, int]:
        """Clean a batch of stored reviews that still contain raw Discord artifacts.

        ## Parameters
            - batch_size: Maximum number of reviews to clean in this batch.

        ## Returns
            A tuple of processed, cleaned, and remaining review counts.
        """

        reviews = await self.database.get_reviews_missing_cleaning(batch_size)
        cleaned_count = 0
        for review in reviews:
            if review.id is None:
                continue
            original_comment = review.comment
            original_translated = review.translated
            self.normalize_review_content(review)
            if review.comment != original_comment or review.translated != original_translated or not review.content_cleaned:
                cleaned_count += 1
            await self.database.update_review_content(
                int(review.id),
                review.comment,
                review.translated,
                content_cleaned=True,
            )

        remaining = await self.database.count_reviews_missing_cleaning()
        return len(reviews), cleaned_count, remaining

    async def _translate_text_to_english(self, text: str) -> str:
        if self.deepl_api_key:
            return await self._translate_text_to_english_deepl(text)
        return await self._translate_text_to_english_chat_completions(text)

    async def _translate_text_to_english_deepl(self, text: str) -> str:
        response = await self.http_client.post(
            f"{self.deepl_api_base_url}/v2/translate",
            headers={
                "Authorization": f"DeepL-Auth-Key {self.deepl_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "text": [text],
                "source_lang": "FR",
                "target_lang": "EN-GB",
                "preserve_formatting": True,
                "split_sentences": "1",
            },
        )
        response.raise_for_status()
        payload = response.json()
        translated = payload["translations"][0]["text"].strip()
        if not translated:
            raise ValueError("Empty translation returned by DeepL.")
        return translated

    async def _translate_text_to_english_chat_completions(self, text: str) -> str:
        assert self.translation_api_base_url is not None
        assert self.translation_api_key is not None
        assert self.translation_api_model is not None

        response = await self.http_client.post(
            f"{self.translation_api_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.translation_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.translation_api_model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Translate customer reviews from French to natural English. "
                            "Preserve meaning, tone, and enthusiasm. Return only the translated review text."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        translated = payload["choices"][0]["message"]["content"].strip()
        if not translated:
            raise ValueError("Empty translation returned by translation API.")
        return translated

    async def send_review_embed(
        self,
        guild: discord.Guild,
        embed: discord.Embed,
        refresh_panel: bool = True,
        review: ReviewRecord | None = None,
    ) -> bool:
        """Send a review embed to the configured channel without breaking the modal flow.

        ## Parameters
            - guild: Guild used to resolve the configured reviews channel.
            - embed: Embed to post in the reviews channel.
            - refresh_panel: Whether to repost the review panel after the review.
            - review: Optional persisted review to link with the published Discord message.

        ## Returns
            True when the embed was sent successfully, otherwise False.
        """

        review_channel = guild.get_channel(self.config.channels.reviews)
        if not isinstance(review_channel, discord.TextChannel):
            logger.warning("Reviews channel %s is missing or not a text channel", self.config.channels.reviews)
            return False
        try:
            message = await review_channel.send(embed=embed)
            if review is not None and review.id is not None:
                review.posted_message_id = message.id
                await self.database.update_review_posted_message(int(review.id), message.id)
            if refresh_panel:
                await self.publish_review_panel(guild)
            return True
        except discord.Forbidden:
            logger.warning("Missing access to reviews channel %s", review_channel.id)
            return False
        except discord.HTTPException:
            logger.exception("Failed to send review embed to channel %s", review_channel.id)
            return False

    async def delete_review_by_id(self, guild: discord.Guild, review_id: int) -> tuple[bool, str]:
        """Delete a stored review and its published Discord message when tracked.

        ## Parameters
            - guild: Guild used to resolve the configured reviews channel.
            - review_id: Database identifier of the review to delete.

        ## Returns
            A tuple containing a success flag and a user-facing status message.
        """

        review = await self.database.get_review_by_id(review_id)
        if review is None:
            return False, "Aucun avis trouvé pour cet identifiant."

        deletion_note = ""
        review_channel = guild.get_channel(self.config.channels.reviews)
        if review.posted_message_id is not None:
            if isinstance(review_channel, discord.TextChannel):
                try:
                    await review_channel.get_partial_message(review.posted_message_id).delete()
                except discord.NotFound:
                    deletion_note = " Le message Discord associé était déjà introuvable."
                except discord.Forbidden:
                    deletion_note = " L'entrée a été supprimée de la base, mais le bot n'a pas pu supprimer le message Discord."
                except discord.HTTPException:
                    logger.exception("Failed to delete review message %s", review.posted_message_id)
                    deletion_note = " L'entrée a été supprimée de la base, mais le message Discord n'a pas pu être supprimé."
            else:
                deletion_note = " L'entrée a été supprimée de la base, mais le salon d'avis configuré est introuvable."

        deleted = await self.database.delete_review(review_id)
        if not deleted:
            return False, "La suppression a échoué, l'avis existe peut-être déjà plus en base."

        return True, f"L'avis `{review_id}` a été supprimé.{deletion_note}"

    async def publish_review_panel(self, guild: discord.Guild) -> bool:
        """Ensure the reviews channel contains a single fresh review panel message.

        ## Parameters
            - guild: Guild used to resolve the configured reviews channel.

        ## Returns
            True when the panel was posted successfully, otherwise False.
        """

        review_channel = guild.get_channel(self.config.channels.reviews)
        if not isinstance(review_channel, discord.TextChannel):
            logger.warning("Reviews channel %s is missing or not a text channel", self.config.channels.reviews)
            return False

        cached = await self.database.get_cache_entry(self._review_panel_cache_key(guild.id))
        if cached is not None:
            message_id = cached["payload"].get("message_id")
            if isinstance(message_id, int):
                try:
                    previous_message = await review_channel.fetch_message(message_id)
                    await previous_message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    logger.warning("Missing access to delete previous review panel %s", message_id)
                except discord.HTTPException:
                    logger.exception("Failed to delete previous review panel %s", message_id)

        try:
            panel_message = await review_channel.send(
                embed=self.embed_factory.review(
                    "Avis clients",
                    "Partagez votre retour sur les scripts achetés via le bouton ci-dessous. Réservé aux clients.",
                ),
                view=ReviewPanelView(),
            )
        except discord.Forbidden:
            logger.warning("Missing access to post review panel in channel %s", review_channel.id)
            return False
        except discord.HTTPException:
            logger.exception("Failed to post review panel in channel %s", review_channel.id)
            return False

        await self.database.set_cache_entry(
            self._review_panel_cache_key(guild.id),
            {"message_id": panel_message.id, "channel_id": review_channel.id},
            utcnow(),
        )
        return True
