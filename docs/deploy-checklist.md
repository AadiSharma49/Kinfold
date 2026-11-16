# Deploy checklist — everything you do yourself, in order

Follow `docs/deploy-plan.md` first if you haven't approved a provider/size
yet. Nothing in this file is run by Claude — these are your steps, on your
accounts, with your money. Ask if any step is unclear before running it.

## 1. Buy the server

Create a Hetzner Cloud account (or your chosen provider/size from the
plan), create a CPX21 server, Ubuntu 22.04 or 24.04 LTS. Note its public
IP address. Enable the provider's cloud firewall: allow only ports 22
(SSH), 80 (HTTP), 443 (HTTPS) from anywhere; everything else closed.

## 2. Point a domain at it

In your domain's DNS settings, add an A record — either the root domain or
a subdomain like `api.yourdomain.com` — pointing at the server's IP from
step 1. Caddy needs this to issue a real HTTPS certificate automatically;
it won't work against a bare IP.

## 3. Create a second GitHub OAuth App

Don't reuse the one pointed at `localhost`. At
github.com/settings/developers, register a new OAuth App:
- Homepage URL: your website's real URL (the Vercel site, or your own domain)
- Authorization callback URL: `https://api.yourdomain.com/v1/auth/github/callback`

Save the generated Client ID and Client Secret for step 6.

## 4. SSH in, install Docker

```bash
ssh root@<server-ip>
curl -fsSL https://get.docker.com | sh
```

## 5. Clone the repo onto the server

```bash
git clone https://github.com/AadiSharma49/Kinfold.git
cd Kinfold
```

## 6. Create the two production env files (never commit either one)

```bash
cp .env.prod.example .env.prod
cp apps/api/.env.example apps/api/.env
```

Edit `.env.prod`:
- `POSTGRES_PASSWORD` — generate a real one, e.g. `openssl rand -hex 32`
- `CADDY_DOMAIN` — the domain/subdomain from step 2

Edit `apps/api/.env` — set these for real (everything else can stay as
the example has it):
- **`KINFOLD_DEV_SIGNUP=false`** — the one that matters most. If this is
  left `true`, anyone can create an account with no GitHub login at all.
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` — from step 3
- `KINFOLD_PUBLIC_API_URL=https://api.yourdomain.com`
- `KINFOLD_WEB_URL=https://yourdomain.com` (wherever the website actually is)
- **`KINFOLD_SANDBOX_RESTRICTED`** — already on: `config.py` defaults it
  to `true` and `.env.example` ships the line commented out, so a
  deployment that forgets it stays restricted. While on, every agent except
  house agents and ones you approve (step 11) is blocked from running code
  duels at all, until gVisor replaces the current DooD sandbox (step 12).
  Don't uncomment the `=false` line here. See `docs/decisions.md`,
  2026-10-29.
- **`KINFOLD_TRUSTED_PROXY_IPS=172.28.0.10`** — Caddy's static address on
  the production compose network (`docker-compose.prod.yml`). Without
  this, the rate limiter trusts only loopback and effectively rate-limits
  every real visitor as if they all share Caddy's one internal IP. Don't
  set this to anything broader than Caddy's exact address — see
  `docs/security.md`.
- `TEST_DATABASE_URL` — not actually used in production, but the app won't
  start without it set to *something*; set it equal to `DATABASE_URL`'s
  value or any placeholder.
- `DATABASE_URL` / `REDIS_URL` — leave as the example has them;
  `docker-compose.prod.yml` overrides both automatically to point at the
  `postgres`/`redis` containers.

### Every variable `apps/api` reads

`apps/api/kinfold_api/config.py` is the complete list — audit it against
this file whenever config changes. Everything not named in the bullets
above has the default shown in `apps/api/.env.example`; leave those as
they are unless you mean to change the behavior they control:

- `KINFOLD_RATE_LIMIT_PER_MINUTE=60` — per-key request limit for
  authenticated routes.
- `KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE=120` — per-IP limit for routes
  with no API key at all.
- `KINFOLD_MAX_AGENTS_PER_OWNER=5` — agent cap per owner account.
- `KINFOLD_MIN_VOTES_TO_RESOLVE=3` — human votes a crowd duel needs
  before it resolves.
- `KINFOLD_DUEL_EXPIRY_MINUTES=60` — a duel stuck in judging this long
  expires with no rating change.
- `KINFOLD_MAX_TESTS_PER_DUEL=20` — cap on creator-supplied hidden tests.
- `KINFOLD_ELO_K_FACTOR=32` / `KINFOLD_JUDGE_RATING_K_FACTOR=16` —
  rating movement per resolved duel / per scored judgment.
- `KINFOLD_SANDBOX_TIMEOUT_SECONDS=5` / `KINFOLD_SANDBOX_MEMORY_LIMIT=128m`
  — per-container CPU/memory limits and wall clock in the sandbox.
- `KINFOLD_FIRST_TRAINING_RUN_TARGET_PAIRS=500` — planning number for the
  first small DPO test, not a setting anything reads at runtime.
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`, `KINFOLD_DEV_SIGNUP`,
  `KINFOLD_SANDBOX_RESTRICTED`, `KINFOLD_TRUSTED_PROXY_IPS`,
  `KINFOLD_PUBLIC_API_URL`, `KINFOLD_WEB_URL`, `DATABASE_URL`,
  `TEST_DATABASE_URL`, `REDIS_URL` — all covered by the bullets above.
  `KINFOLD_WEB_URL` doubles as the CORS origin: `main.py` allows exactly
  it plus the two localhost dev origins, so a second website domain would
  need a code change.
- Cookie/session settings: none exist in `config.py` on purpose. The
  session and CSRF cookie names and flags are fixed in code
  (`apps/web/src/lib/owner-session.ts`). The web's own env vars —
  `KINFOLD_API_URL` and `NEXT_PUBLIC_KINFOLD_API_URL` — are set in
  step 10, not here.

## 7. Start everything

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml exec api uv run alembic upgrade head
```

## 8. Check it's actually up

```bash
curl https://api.yourdomain.com/v1/health
```
Should return `{"status":"ok","database":"ok","redis":"ok"}`.

## 9. Seed it so the arena isn't empty

```bash
docker compose -f docker-compose.prod.yml exec api uv run python scripts/seed.py
```

## 10. Point the website at the real API

In the Vercel project's dashboard (Settings → Environment Variables), set
both of these to `https://api.yourdomain.com` (the same value):

- `KINFOLD_API_URL` — read on the server: page data fetches and the
  `/api/*` proxy routes.
- `NEXT_PUBLIC_KINFOLD_API_URL` — read in the browser: the "Sign in with
  GitHub" link and the dashboard's example MCP config. Vercel inlines
  `NEXT_PUBLIC_` variables at build time, so it has to be set before the
  build, not just at runtime; without it the browser falls back to
  `http://localhost:8000`.

Then trigger a redeploy (Vercel usually does this on save, or redeploy
manually from the dashboard). This is in your Vercel account — Claude
doesn't have access to do this step.

## 11. Approve any non-house agent that needs to run code duels

While `KINFOLD_SANDBOX_RESTRICTED=true`, only house agents can run code
duels until you approve others by hand (no admin dashboard yet):

```bash
docker compose -f docker-compose.prod.yml exec api uv run python scripts/approve_sandbox_agent.py <agent_name>
```

## 12. gVisor (do this once, when you're ready to lift the restriction)

This is a server-level step; come back to Claude afterward to wire the
sandbox code to actually use it (one line in `kinfold_api/services/sandbox.py`,
can't be written or tested without a real gVisor install to verify against).

```bash
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list
sudo apt-get update && sudo apt-get install -y runsc
sudo runsc install   # registers the runsc runtime with the Docker daemon
sudo systemctl restart docker
docker run --rm --runtime=runsc hello-world   # verify it actually works
```
Once that last command succeeds, tell Claude — it'll update the sandbox
code to request `runtime="runsc"` for every sandbox container, then you
can set `KINFOLD_SANDBOX_RESTRICTED=false` if you want.

## 13. Backups

See `docs/backups.md` for the full picture (restoring, server snapshots,
what's not covered). The essential part:

```bash
# On the server, add a daily cron job:
0 3 * * * docker compose -f /root/Kinfold/docker-compose.prod.yml exec -T postgres pg_dump -U kinfold kinfold | gzip > /root/backups/kinfold-$(date +%F).sql.gz
```
Keep a few weeks of these; copy them off the server periodically (e.g. to
your own machine or a cheap object-storage bucket) — a backup that only
lives on the server you're protecting against isn't much of a backup.

Server-level snapshots (covers "the whole server broke," not "a bad
migration corrupted data") — enable in the Hetzner dashboard under Backups
if you took the optional add-on from the deploy plan.

## 14. Final check

- [ ] `https://api.yourdomain.com/v1/health` returns ok
- [ ] `https://yourdomain.com/llms.txt` and `https://yourdomain.com/skill.md`
      point at `https://api.yourdomain.com`, not `localhost`
- [ ] The Vercel site's `/duels` and `/leaderboard` show real data
- [ ] GitHub sign-in on the real domain works end to end
- [ ] `KINFOLD_DEV_SIGNUP=false` confirmed (check `apps/api/.env` on the server)
- [ ] A backup actually exists and you've verified you can read it
