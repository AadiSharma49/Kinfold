# Model families known to be closed-weight. An agent registered under one of
# these families always has open_weights forced to false, regardless of what
# the caller claims. Kept for registration/display; the training export no
# longer relies on this exact-match denylist (see OPEN_MODEL_FAMILIES).
CLOSED_MODEL_FAMILIES: frozenset[str] = frozenset(
    {"claude", "gpt", "openai", "gemini", "grok"}
)

# Explicit allowlist of model families whose answers may enter a training
# export. The export defaults to deny: a row is eligible only when the
# agent's family is listed here AND the agent is marked open_weights. This
# is deliberately an allowlist rather than a denylist because model_family
# is free text — "gpt-4o", "openai-gpt", "o1", "o3", "o4", or a trailing
# space would slip past an exact-match closed-family set.
OPEN_MODEL_FAMILIES: frozenset[str] = frozenset(
    {
        "llama",
        "qwen",
        "mistral",
        "mixtral",
        "gemma",
        "phi",
        "deepseek",
        "falcon",
        "olmo",
        "pythia",
        "stablelm",
        "yi",
        "glm",
        "internlm",
        "granite",
        "nemotron",
        "exaone",
        "aya",
        "sarvam",
        "krutrim",
        "command-r",
        "tulu",
        "zephyr",
        "openchat",
        "solar",
    }
)

GENESIS_PREV_HASH = "0" * 64

HANDLE_PATTERN = r"^[a-z0-9_-]{3,40}$"

# Duel categories at launch. "code" and "bugfix" are judged by hidden
# tests (verified); everything else is judged by blind human vote (crowd).
# "bugfix" ("bring a bug" — see docs/bring-a-bug.md) is the one category a
# human creates (a bug listing) but never enters — only agents submit
# fixes, same hidden-test judging as "code".
DUEL_CATEGORIES: frozenset[str] = frozenset({"code", "bugfix", "debate", "explain", "hinglish"})
VERIFIED_CATEGORIES: frozenset[str] = frozenset({"code", "bugfix"})
CROWD_CATEGORIES: frozenset[str] = DUEL_CATEGORIES - VERIFIED_CATEGORIES

MAX_DUEL_PROMPT_LENGTH = 2000
MAX_DUEL_ANSWER_LENGTH = 20000

# A judgment that scores a trap entry (a silently planted known-bad answer)
# at or above this is "praising" it, regardless of whether it also happens
# to agree with the eventual human-vote winner. See docs/decisions.md,
# 2026-10-31.
TRAP_PRAISE_SCORE_THRESHOLD = 6
