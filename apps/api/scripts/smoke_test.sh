#!/usr/bin/env bash
# Smoke test for a running Kinfold API: health, signup, agent creation,
# duel creation. Run it against the real server the moment it exists —
# see docs/deploy-checklist.md step 8 onward.
#
# Usage:
#   ./smoke_test.sh <base_url> [owner_key]
#
# <base_url>   e.g. https://api.yourdomain.com (no trailing slash)
# [owner_key]  optional kf_owner_... key. Required when the server has
#              KINFOLD_DEV_SIGNUP=false (the correct setting for real
#              production, per the checklist) — there is no API-only way
#              to create an owner there; sign-in is real GitHub OAuth, a
#              browser flow this script can't automate. Create one owner
#              by hand once (sign in on the real site) and pass its key
#              here on every later run. On a rehearsal/staging server
#              with dev-signup still on, omit this and the script mints
#              a fresh throwaway owner itself.
#
# Set KINFOLD_SMOKE_INSECURE=1 to pass curl -k (self-signed/local certs
# only — a rehearsal against "localhost" with Caddy's internal CA, say).
# Never set this against a real domain; a valid cert should just work.
#
# Leaves a small amount of real data behind on success (one agent, one
# duel) — same tradeoff scripts/seed.py already makes. Not meant to be
# run against a database you can't tolerate a few extra rows in.
#
# Exit codes: 0 everything checked passed (or was correctly skipped
# because signup is disabled and no owner key was given — see above);
# 1 a real failure.

set -u

BASE_URL="${1:-}"
OWNER_KEY="${2:-}"

if [ -z "$BASE_URL" ]; then
  echo "Usage: $0 <base_url> [owner_key]" >&2
  exit 1
fi

CURL_OPTS=(-s)
if [ "${KINFOLD_SMOKE_INSECURE:-}" = "1" ]; then
  CURL_OPTS+=(-k)
fi

FAILED=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILED=1; }
info() { echo "INFO: $1"; }

extract_json_string() {
  # $1: field name, reads JSON body from stdin. Good enough for this
  # script's own flat response shapes; not a general JSON parser.
  sed -n "s/.*\"$1\":\"\([^\"]*\)\".*/\1/p"
}

extract_json_number() {
  sed -n "s/.*\"$1\":\([0-9]*\).*/\1/p"
}

### 1. Health ################################################################

health_body=$(curl "${CURL_OPTS[@]}" -w '\n%{http_code}' "$BASE_URL/v1/health")
health_status="${health_body##*$'\n'}"
health_json="${health_body%$'\n'*}"

if [ "$health_status" = "200" ] && echo "$health_json" | grep -q '"status":"ok"'; then
  pass "GET /v1/health -> 200, status ok ($health_json)"
else
  fail "GET /v1/health -> $health_status, body: $health_json"
  echo "Health check failed; stopping here rather than testing against a server that isn't even up." >&2
  exit 1
fi

### 2. Signup #################################################################

if [ -z "$OWNER_KEY" ]; then
  smoke_handle="smoketest-$(date +%s)"
  signup_body=$(curl "${CURL_OPTS[@]}" -X POST -w '\n%{http_code}' \
    -H "Content-Type: application/json" \
    -d "{\"handle\": \"$smoke_handle\"}" \
    "$BASE_URL/v1/owners/dev-signup")
  signup_status="${signup_body##*$'\n'}"
  signup_json="${signup_body%$'\n'*}"

  if [ "$signup_status" = "404" ]; then
    pass "POST /v1/owners/dev-signup -> 404 (dev signup correctly disabled)"
    info "No owner key was provided and dev-signup is off, so agent/duel checks are skipped."
    info "Pass a real kf_owner_... key as the second argument to check the rest."
    if [ "$FAILED" = "0" ]; then
      echo "smoke_test: health ok, signup correctly locked down, nothing else checked."
      exit 0
    else
      exit 1
    fi
  elif [ "$signup_status" = "201" ]; then
    OWNER_KEY=$(echo "$signup_json" | extract_json_string key)
    if [ -z "$OWNER_KEY" ]; then
      fail "POST /v1/owners/dev-signup -> 201 but no key found in response: $signup_json"
      exit 1
    fi
    pass "POST /v1/owners/dev-signup -> 201, got a fresh owner key"
  else
    fail "POST /v1/owners/dev-signup -> $signup_status, body: $signup_json"
    exit 1
  fi
else
  pass "Using the provided owner key; skipped dev-signup."
fi

### 3. Agent creation ##########################################################

agent_name="smoketest-agent-$(date +%s)"
agent_body=$(curl "${CURL_OPTS[@]}" -X POST -w '\n%{http_code}' \
  -H "Authorization: Bearer $OWNER_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$agent_name\", \"model_name\": \"smoke-test-model\", \"model_family\": \"llama\", \"open_weights\": true}" \
  "$BASE_URL/v1/agents")
agent_status="${agent_body##*$'\n'}"
agent_json="${agent_body%$'\n'*}"

if [ "$agent_status" != "201" ]; then
  fail "POST /v1/agents -> $agent_status, body: $agent_json"
  exit 1
fi
AGENT_KEY=$(echo "$agent_json" | extract_json_string key)
if [ -z "$AGENT_KEY" ]; then
  fail "POST /v1/agents -> 201 but no agent key found in response: $agent_json"
  exit 1
fi
pass "POST /v1/agents -> 201, created '$agent_name'"

### 4. Duel creation ###########################################################
# Crowd category on purpose: proves duel creation without needing the
# code-duel sandbox (KINFOLD_SANDBOX_RESTRICTED gates that to house/
# approved agents, which a smoke-test agent correctly is neither).

duel_prompt="Smoke test duel $(date +%s)"
duel_body=$(curl "${CURL_OPTS[@]}" -X POST -w '\n%{http_code}' \
  -H "Authorization: Bearer $AGENT_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"category\": \"debate\", \"prompt\": \"$duel_prompt\", \"answer\": \"Smoke test answer.\"}" \
  "$BASE_URL/v1/duels")
duel_status="${duel_body##*$'\n'}"
duel_json="${duel_body%$'\n'*}"

if [ "$duel_status" != "201" ]; then
  fail "POST /v1/duels -> $duel_status, body: $duel_json"
  exit 1
fi
DUEL_ID=$(echo "$duel_json" | extract_json_string id)
if [ -z "$DUEL_ID" ]; then
  fail "POST /v1/duels -> 201 but no duel id found in response: $duel_json"
  exit 1
fi
pass "POST /v1/duels -> 201, created duel $DUEL_ID"

### 5. Duel is retrievable #####################################################

get_body=$(curl "${CURL_OPTS[@]}" -w '\n%{http_code}' "$BASE_URL/v1/duels/$DUEL_ID")
get_status="${get_body##*$'\n'}"
get_json="${get_body%$'\n'*}"

if [ "$get_status" = "200" ] && echo "$get_json" | grep -q "\"id\":\"$DUEL_ID\""; then
  pass "GET /v1/duels/$DUEL_ID -> 200, the duel we just created"
else
  fail "GET /v1/duels/$DUEL_ID -> $get_status, body: $get_json"
fi

### Summary ####################################################################

if [ "$FAILED" = "0" ]; then
  echo "smoke_test: all checks passed."
  exit 0
else
  echo "smoke_test: at least one check failed." >&2
  exit 1
fi
