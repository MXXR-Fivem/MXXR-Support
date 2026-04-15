# Déploiement

## But

Le dépôt supporte une stack Docker séparée:
- Stack A: site perso inchangé
- Stack B: `bot-api` + `discord-bot` optionnel

## Fichiers utiles
- Compose: `deploy/docker-compose.bot-stack.yml`
- Wrapper: `deploy/manage-bot-stack.sh`
- Exemple API: `deploy/docker/.env.api.example`
- Runtime bot: `.env`

## Préparation
```bash
cp .env.example .env
cp deploy/docker/.env.api.example deploy/docker/.env.api
cp config.example.yaml config.yaml
mkdir -p data
```

À régler ensuite:
- Dans `.env`: variables `DISCORD_*`, `TEBEX_*`, `DATABASE_PATH=data/bot.sqlite3`, `DATA_DIR=data`
- Dans `deploy/docker/.env.api`: `BOT_API_BIND_IP=0.0.0.0`, `BOT_API_PORT=8082`, `REVIEW_API_BEARER_TOKEN`
- Laisser `REVIEW_API_ALLOWED_ORIGINS` vide si l’API est appelée uniquement en server-to-server

## Démarrage
API seule:

```bash
./deploy/manage-bot-stack.sh up -d --build bot-api
```

Bot + API:

```bash
./deploy/manage-bot-stack.sh --profile bot-runtime up -d --build
```

Commande brute équivalente:

```bash
docker compose --env-file deploy/docker/.env.api -f deploy/docker-compose.bot-stack.yml up -d --build bot-api
```

## Accès et vérification
Exemple d’exposition:

```env
BOT_API_BIND_IP=0.0.0.0
BOT_API_PORT=8082
```

Tests:

```bash
curl http://127.0.0.1:8082/healthz
curl -H "Authorization: Bearer <token>" "http://127.0.0.1:8082/api/reviews/random?limit=3"
```

Depuis une autre machine:

```bash
curl http://<server-ip>:8082/healthz
```

## Notes
- Ne jamais exposer le Bearer token côté navigateur
- `REVIEW_API_ALLOWED_ORIGINS` n’est pas utile pour un trafic purement server-to-server
- Le rich presence du bot alterne toutes les 10 secondes entre membres Discord et stats Tebex, avec cache Tebex pour éviter un fetch à chaque switch
