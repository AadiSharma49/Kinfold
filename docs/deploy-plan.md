# Deployment plan — for approval, nothing bought or deployed yet

A single VPS running everything: API, worker, Postgres, Redis, Caddy for
HTTPS. This is a plan to review, not an action taken — see
`docs/deploy-checklist.md` for the numbered steps once you approve.

## Recommended provider and size

**Hetzner Cloud, CPX21** — 3 vCPU, 4 GB RAM, 80 GB SSD, 20 TB traffic.
**~$5.39/month** (billed hourly, cancel anytime, no contract).

Why this one and this size:
- **Why Hetzner over DigitalOcean/Linode/AWS Lightsail**: same or better
  specs for roughly half the price at this tier (DigitalOcean's closest
  equivalent, a 2 vCPU / 4 GB droplet, is ~$24/month). Hetzner has no free
  tier gimmicks and no surprise egress billing at this traffic level — the
  20 TB included is far more than Kinfold will use early on. Downside:
  support is email-only and the control panel is more bare-bones than
  DigitalOcean's; acceptable for a single small server.
- **Why not the cheapest tier (CPX11, 2 vCPU / 2 GB, ~$4/month)**: Postgres,
  Redis, the API process, and a sandbox container all running at once on
  2 GB leaves very little headroom — a single busy code duel (a fresh
  container per test case) would risk OOM-killing something else on the
  box. 4 GB gives real margin without jumping to a much pricier tier.
  Revisit if traffic actually requires more.
- **Why not a bigger tier yet**: no real usage data exists. Start small,
  resize up later if metrics say so — Hetzner resizes are a few minutes of
  downtime, not a migration.

**Add-on, optional but recommended**: Hetzner's automatic snapshot backups,
+20% of server cost (~$1.08/month) — daily snapshots, 7 kept. Covers "the
server got corrupted/hacked," not a substitute for the database backup
step in the deploy checklist (which covers "bad migration wiped data").

**Total: ~$5.39/month, or ~$6.47/month with backups.**

## Domain

Needs one real domain (or a subdomain of one you already own) for Caddy to
get a free HTTPS certificate automatically — Caddy can't do this for a bare
IP address. A cheap option: a `.dev` or `.app` domain from Porkbun or
Namecheap, roughly $10-15/year. If you already own a domain for anything
else, a subdomain like `api.yourdomain.com` works and costs nothing extra.

## Topology — everything on the one server

```
                    ┌─────────────────────────────────────┐
  Internet ───443──▶│  Caddy (reverse proxy + auto HTTPS)  │
                    └───────────────┬───────────────────────┘
                                    │ :8000
                    ┌───────────────▼───────────────────────┐
                    │  api container (FastAPI, uvicorn)      │
                    │  — also runs the sandbox today (DooD)  │
                    └───────┬─────────────────────┬──────────┘
                            │                      │
                    ┌───────▼──────┐       ┌───────▼──────┐
                    │  Postgres     │       │  Redis        │
                    │  (not public) │       │  (not public) │
                    └───────────────┘       └───────────────┘
                            ▲
                            │ mounts /var/run/docker.sock
                    ┌───────┴──────────────────────┐
                    │  host Docker daemon           │
                    │  spawns one sandbox container │
                    │  per test case (DooD)         │
                    └────────────────────────────────┘
```

**Honest note on "worker"**: the task asked for API, worker, Postgres,
Redis, Caddy as five pieces. Today's codebase doesn't actually have a
separate worker process yet — `apps/api` runs the sandbox inline, inside
the same request that resolves a code duel (see `kinfold_api/services/duels.py`).
This plan reserves a "worker" slot in the topology for when that split
happens (splitting sandbox execution into its own process, talking to the
API over a queue, is real future hardening work — better isolation, since
a bug in the public API wouldn't also have direct Docker-socket access).
For this first deployment, **api and worker are the same container** —
building the actual split is a separate, later task, not bundled into
getting Kinfold public for the first time.

**Already built and tested** (earlier work): `docker-compose.prod.yml`
(api + postgres + redis + caddy), `apps/api/Dockerfile`, `infra/caddy/Caddyfile`,
`.env.prod.example`. This plan uses what already exists — nothing new to
build for the deployment itself, only steps to run it on a real server.

## What's already handled, what's net-new on the server

| Concern | Status |
|---|---|
| Postgres/Redis not exposed publicly | Already in `docker-compose.prod.yml` |
| HTTPS | Caddy, automatic, already configured |
| `KINFOLD_DEV_SIGNUP=false` in production | Documented in `apps/api/README.md`, must be set on the server |
| A second GitHub OAuth App for the real domain | Net-new — can't reuse the localhost one |
| Sandbox isolation (gVisor vs restriction) | Restriction shipped today (task 2); gVisor install is a server step, in the checklist |
| Backups | Net-new — see the checklist |
| Firewall | Net-new — Hetzner's cloud firewall, allow only 22/80/443 |

## Monthly cost summary

| Item | Cost |
|---|---|
| Hetzner CPX21 | ~$5.39/mo |
| Snapshot backups (optional) | ~$1.08/mo |
| Domain (if you need a new one) | ~$10-15/year (~$1/mo) |
| **Total** | **~$6-8/month** |

Nothing here has been purchased or deployed. Say go-ahead and name a
provider account to use, and I'll work through `docs/deploy-checklist.md`
with you step by step.
