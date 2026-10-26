# Kinfold API — production image.
#
# Runs with access to the host's Docker socket (mounted at deploy time, see
# docker-compose.prod.yml) so it can spawn the code-duel sandbox containers
# as siblings, not nested inside this one. That access is equivalent to root
# on the host — a known, accepted tradeoff for this app, not an oversight.

FROM python:3.12-slim AS base

# The Docker CLI itself (not a daemon) — needed to talk to the mounted
# host socket. The `docker` Python package alone is not enough; it shells
# out to nothing, but having the CLI available matches how this was
# developed and verified locally with Docker Desktop.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && curl -fsSL https://get.docker.com | sh \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# Not `uv run` here on purpose: uv run re-evaluates the project's default
# dependency groups on every invocation, which pulls dev-only packages
# (ruff, pytest) over the network at every container start even though the
# build already excluded them with --no-dev. Invoking the venv's own
# uvicorn directly skips that resync entirely.
CMD ["uvicorn", "kinfold_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
