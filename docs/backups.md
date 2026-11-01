# Backups

What's backed up, how, and how to actually restore from one. The daily
cron command itself already lives in `docs/deploy-checklist.md` step 13 —
this doc is the fuller picture: why, what's covered, what isn't, and how
to prove a backup is actually usable before you need it.

## What's backed up

**The Postgres database** — the only thing that actually matters if
something goes wrong. Everything else (API code, Docker images, Caddy
config) is in git and can be redeployed from scratch; the database is the
one thing with no other copy.

```bash
# daily cron job on the server, see docs/deploy-checklist.md step 13
0 3 * * * docker compose -f /root/Kinfold/docker-compose.prod.yml exec -T postgres pg_dump -U kinfold kinfold | gzip > /root/backups/kinfold-$(date +%F).sql.gz
```

Keep a few weeks of these (`find /root/backups -mtime +21 -delete` in the
same cron entry, or a separate one, once there's more than a handful of
files to manage).

## Get them off the server

A backup that only lives on the server you're protecting against isn't
much of a backup — if the server itself is lost (disk failure, account
issue, a bad `rm`), the backups go with it. Copy them off periodically:

```bash
# from your own machine, pull the latest backup down
scp root@<server-ip>:/root/backups/kinfold-$(date +%F).sql.gz ./
```

Or point the same cron job at a cheap object-storage bucket (Hetzner
Storage Box, Backblaze B2, or similar) instead of a local directory, if
you want this automated rather than a manual pull. Not set up yet —
manual `scp` is the current plan until there's a real reason to automate
it.

## Server-level snapshots — a different, complementary layer

Hetzner's automatic snapshot backups (optional add-on, ~20% of server
cost, enabled in the Hetzner dashboard) cover "the whole server broke or
got compromised" — restore the entire disk image. This does **not**
replace the pg_dump backups above: a snapshot taken right after a bad
migration corrupted data would faithfully preserve the corruption. Use
pg_dump backups to recover from a bad deploy/migration/accidental delete;
use a snapshot to recover from losing the server itself.

## Verify a backup is actually restorable

A backup you've never tested restoring from is a guess, not a backup.
Periodically (recommended: after setting this up, and again after any
schema change), actually restore one somewhere other than production:

```bash
# on your own machine, or a scratch server — NOT against production
gunzip -c kinfold-2026-11-01.sql.gz | psql -U kinfold -d kinfold_restore_test
```

If that fails, the backup process is broken and you want to know now, not
during an actual incident.

## What's not covered

- Redis is not backed up — it holds rate-limit counters and nothing that
  needs to survive a restart; losing it just resets rate-limit windows.
- Uploaded files: there are none yet (no file uploads in the product as of
  this writing) — revisit this doc if that changes.
