# MXXR Discord Bot

Bot Discord Python pour support FiveM/Tebex, avec `discord.py`, `SQLite` et `httpx`.

## Points clés
- Commandes publiques et staff
- Tickets, giveaways, sondages, avis clients et posts sociaux
- API Bearer pour exposer des avis aléatoires
- Modération des invites Discord et protection anti-abus sur `/ban`
- Présence enrichie: toutes les 10 secondes, le bot alterne entre le nombre de membres Discord et les stats Tebex
- Les stats Tebex ne sont pas refetch à chaque switch: elles sont gardées en cache puis rafraîchies selon `presence.refresh_interval_minutes`

## Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config.example.yaml config.yaml
```

Configurer ensuite `.env` et `config.yaml`.

## Lancement
```bash
python3 -m bot.main
```

API d’avis seule:

```bash
python3 -m bot.api_main
```

## Variables importantes
- `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, `DISCORD_GUILD_ID`
- `TEBEX_API_KEY`, `TEBEX_BASE_URL`
- `REVIEW_API_HOST`, `REVIEW_API_PORT`, `REVIEW_API_BEARER_TOKEN`, `REVIEW_API_ALLOWED_ORIGINS`
- `DEEPL_API_KEY` ou `TRANSLATION_API_*`
- `LOG_LEVEL`, `ENVIRONMENT`, `CONFIG_PATH`, `DATABASE_PATH`, `DATA_DIR`

## Tebex et présence
- `bot/services/tebex_client.py`: appels HTTP Tebex
- `bot/services/tebex_service.py`: agrégation et cache des métriques
- `bot/tasks/presence.py`: alternance présence Discord/Tebex
- `total_sales`: paiements complétés
- `unique_customers`: UUID joueur, sinon ID, sinon email/nom en fallback

## Déploiement
- Stack Docker: `deploy/docker-compose.bot-stack.yml`
- Documentation d’exploitation: `deploy/README.md`
