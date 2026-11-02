# Model families known to be closed-weight. An agent registered under one of
# these families always has open_weights forced to false, regardless of what
# the caller claims.
CLOSED_MODEL_FAMILIES: frozenset[str] = frozenset(
    {"claude", "gpt", "openai", "gemini", "grok"}
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
