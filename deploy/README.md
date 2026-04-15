# Deployment

## Objective

This repository now supports a fully separated stack for the review API:

- Stack A: existing personal site, untouched
- Stack B: `bot-api` container + optional `discord-bot` container on a dedicated Docker network

## Files

- Compose stack: `deploy/docker-compose.bot-stack.yml`
- API-only runtime: `python -m bot.api_main`
- Bot env file: `.env`
- API env file example: `deploy/docker/.env.api.example`

## 1. Prepare stack B

Create the runtime files expected by the compose stack:

```bash
cp .env.example .env
cp deploy/docker/.env.api.example deploy/docker/.env.api
cp config.example.yaml config.yaml
mkdir -p data
```

Then edit `.env` for the Discord bot runtime and `deploy/docker/.env.api` for the API stack.

In `deploy/docker/.env.api`:

- set `BOT_API_BIND_IP=0.0.0.0` to expose the API directly on the machine IP
- keep `BOT_API_PORT` on a free host port, for example `8082`
- set `REVIEW_API_BEARER_TOKEN`
- if the API is consumed only server-to-server from Next.js on Vercel, leave `REVIEW_API_ALLOWED_ORIGINS` empty

In `.env`:

- keep your existing `DISCORD_*`, `TEBEX_*`, and other bot variables
- set `DATABASE_PATH=data/bot.sqlite3` and `DATA_DIR=data` if you want the bot and API to use the same SQLite file
- you can keep the `REVIEW_API_*` variables here too if you also still run the bot outside Docker, but Docker no longer depends on them for `discord-bot`

## 2. Start the isolated API stack

Use the wrapper so Docker Compose reads `deploy/docker/.env.api` for variable interpolation such as `BOT_API_PORT`. `env_file` inside the compose service only affects container environment variables, not the compose file itself.

API only:

```bash
./deploy/manage-bot-stack.sh up -d --build bot-api
```

Optional full Stack B including the Discord bot container:

```bash
./deploy/manage-bot-stack.sh --profile bot-runtime up -d --build
```

Equivalent raw command if you do not want the wrapper:

```bash
docker-compose --env-file deploy/docker/.env.api -f deploy/docker-compose.bot-stack.yml up -d --build bot-api
```

If your server has the newer Docker Compose plugin, the equivalent command is:

```bash
docker compose --env-file deploy/docker/.env.api -f deploy/docker-compose.bot-stack.yml up -d --build bot-api
```

This starts:

- `mxxr-bot-api`: standalone review API published on `${BOT_API_BIND_IP}:${BOT_API_PORT}`
- `mxxr-discord-bot`: optional Discord bot runtime, isolated in the same stack profile

## 3. Direct IP access

For a simple server-to-server call from Next.js, you do not need a custom domain. Publish the API on the VPS public IP with a dedicated port, for example:

```env
BOT_API_BIND_IP=0.0.0.0
BOT_API_PORT=8082
```

Then allow that port in your firewall/security group and call:

```text
http://<server-ip>:8082
```

## 4. Verification

From the VM:

```bash
curl http://127.0.0.1:8082/healthz
curl -H "Authorization: Bearer <token>" "http://127.0.0.1:8082/api/reviews/random?limit=3"
```

From another machine or from your Next.js server runtime:

```bash
curl http://<server-ip>:8082/healthz
curl -H "Authorization: Bearer <token>" "http://<server-ip>:8082/api/reviews/random?limit=3"
```

## Security notes

- Keep the Bearer token only in Vercel server-side environment variables.
- Call this API only from server components, route handlers, or server actions.
- Never expose the Bearer token in browser code.
- `REVIEW_API_ALLOWED_ORIGINS` is not needed for pure server-to-server traffic.
