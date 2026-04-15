from __future__ import annotations

from urllib.parse import parse_qs, urlparse
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from bot.app import BotContainer


TEBEX_INFO_DESCRIPTION = """🇫🇷 **FR**

**Instructions pour acheter un script sur la boutique Tebex**

**Prérequis :**
Afin de pouvoir utiliser le(s) script(s) sur votre serveur, vous devez impérativement acheter avec le meme compte FiveM (CFX) que celui utilise pour payer votre License Key (Patreon ou non).

⚠️ Aucun remboursement ne sera effectue si cette condition n'est pas respectee.

Vous pouvez commander les scripts ici :
https://mxxr.tebex.io/

**Support :**
En cas de probleme, ouvrez un ticket dans : ⁠🔖｜tickets en detaillant votre probleme.
La plupart des scripts sont disponibles en francais et anglais, avec possibilite d'ajouter d'autres langues (cela est precise dans chaque description).
Les scripts sont cryptes cote client et serveur, a l'exception :
- du fichier config
- du fichier traduction
Il est recommande de retelecharger regulierement vos scripts afin de profiter des dernieres mises a jour.

⚠️ La documentation peut repondre a la majorite des questions (installation, configuration, etc.)
Merci de la consulter avant toute demande d'aide :
https://mxxr.gitbook.io/mxxr-wiki

Merci pour votre comprehension,
Cordialement MXXR

🇬🇧 **EN**

**Instructions to purchase a script from the Tebex store**

**Requirements :**
To use the script(s) on your server, you must purchase them with the same FiveM (CFX) account used to pay for your server License Key (Patreon or not).

⚠️ No refund will be given if this condition is not respected.

You can buy scripts here:
https://mxxr.tebex.io/

**Support :**
If you encounter any issue, open a ticket in : ⁠🔖｜tickets and describe your problem.
Most scripts are available in French and English, with the possibility to add other languages (this is specified in each script description).
Scripts are encrypted on both client and server side, except:
- config file
- translation file
It is recommended to re-download your scripts regularly to get the latest updates.

⚠️ Documentation may answer most of your questions (installation, configuration, etc.)
Please check it before asking for support:
https://mxxr.gitbook.io/mxxr-wiki

Thank you for your understanding,
Best regards, MXXR"""


SCRIPT_INFO_DESCRIPTION = """🇫🇷 **FR**

⚠️ **Information importante**

Afin de pouvoir utiliser le(s) script(s) sur votre serveur, vous devez imperativement effectuer l'achat avec le meme compte FiveM (CFX) que celui utilise pour payer votre License Key (Patreon ou non).
Aucun remboursement ne sera effectue si cette condition n'est pas respectee.

Je precise egalement que les fichiers client et serveur sont cryptes.
C'est pourquoi un maximum d'options sont disponibles dans le fichier config afin de vous permettre de personnaliser le script.

📖 Afin de faire fonctionner correctement le script, merci de lire le fichier README.

🇬🇧 **EN**

⚠️ **Important information**

To use the script(s) on your server, you must purchase them with the same FiveM (CFX) account used to pay for your server License Key (Patreon or not).
No refund will be given if this condition is not respected.

Please note that both client and server files are encrypted.
That's why most customization options are available in the config file.

📖 To ensure the script works correctly, please read the README file."""


def build_tebex_info_embed(container: BotContainer) -> discord.Embed:
    embed = container.embeds.info("Informations Tebex", TEBEX_INFO_DESCRIPTION)
    return embed


def build_script_info_embed(
    container: BotContainer,
    title: str,
    video_url: str,
    tebex_url: str,
    doc_url: str | None = None,
) -> discord.Embed:
    embed = container.embeds.social_post(title, SCRIPT_INFO_DESCRIPTION)
    embed.url = video_url
    embed.add_field(name="🎥 Video", value=video_url, inline=False)
    embed.add_field(name="🛒 Tebex", value=tebex_url, inline=False)
    if doc_url:
        embed.add_field(name="📖 Documentation", value=doc_url, inline=False)
    thumbnail_url = _get_video_preview_url(video_url)
    if thumbnail_url is not None:
        embed.set_image(url=thumbnail_url)
    return embed


def build_script_update_embed(
    container: BotContainer,
    title: str,
    updates: str,
    video_url: str | None = None,
) -> discord.Embed:
    embed = container.embeds.info(title, updates[:4096])
    if video_url:
        embed.url = video_url
        embed.add_field(name="🎥 Video", value=video_url, inline=False)
        thumbnail_url = _get_video_preview_url(video_url)
        if thumbnail_url is not None:
            embed.set_image(url=thumbnail_url)
    return embed


def _get_video_preview_url(video_url: str) -> str | None:
    video_id = _extract_youtube_video_id(video_url)
    if video_id is None:
        return None
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"


def _extract_youtube_video_id(video_url: str) -> str | None:
    parsed = urlparse(video_url)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if host in {"youtu.be", "www.youtu.be"} and path:
        return path.split("/")[0]

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if path == "watch":
            query_video_id = parse_qs(parsed.query).get("v", [])
            return query_video_id[0] if query_video_id else None
        if path.startswith("shorts/") or path.startswith("embed/"):
            parts = path.split("/")
            return parts[1] if len(parts) > 1 else None

    return None
