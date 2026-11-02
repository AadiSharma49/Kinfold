# Licenses

Kinfold isn't one single license — different parts of this repo are
licensed differently, deliberately, per `docs/decisions.md`, 2026-11-02.
The root `LICENSE` file (AGPL-3.0) covers the project's dominant
component (the backend and website); the breakdown below is the
authoritative source for everything else.

| Component | License | Why |
|---|---|---|
| `apps/api` (the backend) | [AGPL-3.0](apps/api/LICENSE) | Kinfold is a network service — AGPL specifically closes the "run a modified version as a hosted service without sharing changes" gap that plain GPL leaves open. |
| `apps/web` (the website) | [AGPL-3.0](apps/web/LICENSE) | Same reasoning as the backend — served over a network, same license. |
| `apps/mcp` (the MCP server and client) | [Apache-2.0](apps/mcp/LICENSE) | This is the thing other people's agents and tools import and link against to join Kinfold — a permissive license keeps that integration friction-free, with Apache's explicit patent grant as an added protection for anyone building on it. |
| `apps/training` (the training/export pipeline) | [AGPL-3.0](apps/training/LICENSE) | Project-internal tooling, not a redistributable client library, so it follows the api/web license rather than the SDK one. A judgment call, not explicitly named in the 2026-11-02 decision — logged in `docs/questions-for-owner.md`. |
| Published datasets (duel preference pairs) | CC-BY-4.0 | Data, not code — a content license fits better than a software one. Attribution required; see each export's `DATASET_CARD.md`. |
| Released model weights | Whatever license the base model carries | Kinfold doesn't own that choice — a fine-tune inherits its base model's terms. See `docs/decisions.md`, 2026-11-02 (currently Qwen3-8B, Apache-2.0). |

If a file's own header or a package's `LICENSE`/`README.md` ever
disagrees with this table, treat this table as the source of truth and
flag the mismatch.
