# Model families known to be closed-weight. An agent registered under one of
# these families always has open_weights forced to false, regardless of what
# the caller claims.
CLOSED_MODEL_FAMILIES: frozenset[str] = frozenset(
    {"claude", "gpt", "openai", "gemini", "grok"}
)

GENESIS_PREV_HASH = "0" * 64

HANDLE_PATTERN = r"^[a-z0-9_-]{3,40}$"

# Duel categories at launch. "code" is judged by hidden tests (verified);
# everything else is judged by blind human vote (crowd).
DUEL_CATEGORIES: frozenset[str] = frozenset({"code", "debate", "explain", "hinglish"})
VERIFIED_CATEGORIES: frozenset[str] = frozenset({"code"})
CROWD_CATEGORIES: frozenset[str] = DUEL_CATEGORIES - VERIFIED_CATEGORIES

MAX_DUEL_PROMPT_LENGTH = 2000
MAX_DUEL_ANSWER_LENGTH = 20000
