# MXXR Discord Bot

Bot Discord professionnel pour boutique FiveM / Tebex, construit en Python avec `discord.py`, `aiosqlite` et `httpx`.

Le thème visuel par défaut du projet est aligné sur la boutique `https://mxxr.tebex.io/`:
- accent principal bleu `#386bff`
- base secondaire `#2f3348`
- fond sombre `#1a1d30`
- branding centré sur `MXXR`

## Choix techniques
- `discord.py` a été retenu pour sa stabilité, son support natif des slash commands, des views persistantes et des tasks.
- `SQLite` fournit une persistance simple mais propre, facilement remplaçable plus tard par PostgreSQL.
- `httpx` centralise les intégrations HTTP asynchrones.
- Configuration hybride:
  - `.env` pour les secrets et variables runtime
  - `config.yaml` pour le fonctionnel métier et les IDs Discord

## Fonctionnalités
- Commandes publiques: `/help`, `/avatar`, `/info`, `/ping`
- Commandes staff: `/help-admin`, `/ticket-panel`, `/social-post`, `/tebex-info`, `/script-info`, `/script-update`, `/review-panel`, `/review-import-channel`, `/review-clean-backfill`, `/review-translate-backfill`, `/review-delete`, `/giveaway-create`, `/giveaway-reroll`, `/poll-create`, `/ban`, `/clear`
- Tickets:
  - création via bouton ou `/ticket-create`
  - catégories configurables
  - channel privé
  - fermeture par bouton
  - transcript texte
  - logs dédiés
- Giveaways:
  - création staff via `/giveaway-create`
  - durée configurable
  - participation par bouton
  - tirage automatique
  - reroll via `/giveaway-reroll`
- Avis:
  - rôle `customer` requis pour soumettre un avis
  - panneau d’avis
  - modal utilisateur
  - validation note/commentaire
  - publication formatée en salon dédié
  - traduction anglaise stockée en base
  - API Bearer pour exposer des avis aléatoires au portfolio
- Sondages:
  - création staff via `/poll-create`
  - votes par boutons
  - résultats édités en direct
- Présence enrichie Tebex:
  - total des ventes complétées
  - clients uniques par UUID client, puis ID, puis email en fallback
  - pagination gérée côté Tebex
  - cache local pour limiter les appels
- Réseaux sociaux:
  - publication manuelle via `/social-post`
  - embed uniforme pour YouTube, X et TikTok
  - aucune intégration de fetch automatique, uniquement du post manuel
- Modération:
  - suppression des invites Discord hors salon autorisé
  - exemptions de rôles
  - logs
- Protection anti-abus sur le ban du bot:
  - `/ban` réservé aux rôles autorisés
  - retrait automatique du rôle ban si plus de N bans dans la fenêtre configurée
  - alerte staff

## Architecture
```text
bot/
  app.py
  main.py
  commands/
    public/
    staff/
  cogs/
  config/
  constants/
  embeds/
  events/
  guards/
  modals/
  models/
  services/
  storage/
  tasks/
  utils/
  views/
tests/
```

## Installation
1. Créer un environnement Python 3.11+.
2. Installer les dépendances:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
3. Copier les fichiers d’exemple:
```bash
cp .env.example .env
cp config.example.yaml config.yaml
```
4. Renseigner les variables réelles dans `.env` et les IDs Discord dans `config.yaml`.

## Lancement
```bash
python -m bot.main
```

API d’avis seule:

```bash
python -m bot.api_main
```

## Variables d’environnement
- `DISCORD_TOKEN`: token du bot
- `DISCORD_CLIENT_ID`: application ID Discord
- `DISCORD_GUILD_ID`: guild de dev pour sync rapide optionnelle
- `TEBEX_API_KEY`: secret plugin Tebex
- `TEBEX_BASE_URL`: base URL API Tebex, par défaut `https://plugin.tebex.io`
- `BOT_PRIMARY_COLOR`: surcharge optionnelle de la couleur branding
- `REVIEW_API_HOST`: hôte d’écoute de l’API d’avis, par défaut `127.0.0.1`
- `REVIEW_API_PORT`: port d’écoute de l’API d’avis, par défaut `8081`
- `REVIEW_API_BEARER_TOKEN`: token Bearer requis pour l’API d’avis
- `REVIEW_API_ALLOWED_ORIGINS`: liste séparée par des virgules des origines autorisées pour le CORS navigateur
- `DEEPL_API_BASE_URL`: base URL DeepL, par défaut `https://api-free.deepl.com`
- `DEEPL_API_KEY`: clé DeepL API Free pour traduire les avis en anglais
- `TRANSLATION_API_BASE_URL`: base URL d’une API de traduction compatible OpenAI Chat Completions
- `TRANSLATION_API_KEY`: clé Bearer de l’API de traduction
- `TRANSLATION_API_MODEL`: modèle utilisé pour traduire les avis en anglais
- `LOG_LEVEL`: niveau de logs
- `ENVIRONMENT`: `development`, `staging`, `production`
- `CONFIG_PATH`: chemin vers la config YAML
- `DATABASE_PATH`: chemin SQLite
- `DATA_DIR`: répertoire runtime

## Tebex
Le service Tebex est séparé entre:
- `bot/services/tebex_client.py`: appels HTTP bruts et pagination
- `bot/services/tebex_service.py`: cache et agrégation métier

Le calcul suit cette logique:
1. Récupération de toutes les pages de paiements via `paged`.
2. Filtrage sur les paiements `complete`.
3. `total_sales = nombre de paiements complets`.
4. `unique_customers`:
   - `player.uuid` si présent
   - sinon `player.id`
   - sinon email normalisé en minuscules
5. Mise en cache locale en base avec TTL configurable côté code.

## Personnalisation des embeds
Le branding est centralisé dans:
- `bot/embeds/factory.py`
- `branding` dans `config.yaml`

Tous les embeds passent par la même factory:
- `success`
- `error`
- `warning`
- `info`
- `ticket`
- `review`
- `poll`
- `giveaway`
- `moderation`
- `social_post`

## Ajouter une commande
1. Ajouter la logique de réponse ou de préparation dans `bot/commands/public` ou `bot/commands/staff`.
2. Ajouter l’enregistrement slash command dans le cog métier concerné sous `bot/cogs/`.
3. Réutiliser les services depuis `bot.app.BotContainer`.
4. Si nécessaire, ajouter une view ou une modal dédiée.

## Persistance
Tables SQLite actuelles:
- `tickets`
- `giveaways`
- `giveaway_entries`
- `reviews`
- `polls`
- `poll_votes`
- `ban_actions`
- `social_posts`
- `cache_entries`

## API avis
- Route: `GET /api/reviews/random?limit=6`
- Header requis: `Authorization: Bearer <token>`
- CORS: si l’API est appelée depuis un front navigateur, définir `REVIEW_API_ALLOWED_ORIGINS` avec les domaines autorisés
- Réponse: avis aléatoires avec `author_name`, `scripts`, `rating`, `comment_fr`, `comment_en`, `created_at`

## Déploiement Docker isolé
- Stack Docker dédiée: `deploy/docker-compose.bot-stack.yml`
- Runtime API seul: `python -m bot.api_main`
- Documentation d’exploitation: `deploy/README.md`

## TODO honnêtes
- Ajouter un export transcript HTML ou Markdown plus riche si souhaité.
- Ajouter une vraie synchronisation persistante des vues de sondage si tu veux aussi reconstruire dynamiquement tous les messages actifs après redémarrage avec leur état exact.

## Fichiers principaux
- [bot/main.py](/home/ubuntu/MXXR-Support/bot/main.py)
- [bot/app.py](/home/ubuntu/MXXR-Support/bot/app.py)
- [bot/services/tebex_client.py](/home/ubuntu/MXXR-Support/bot/services/tebex_client.py)
- [bot/services/tebex_service.py](/home/ubuntu/MXXR-Support/bot/services/tebex_service.py)
- [bot/storage/database.py](/home/ubuntu/MXXR-Support/bot/storage/database.py)
- [bot/embeds/factory.py](/home/ubuntu/MXXR-Support/bot/embeds/factory.py)
