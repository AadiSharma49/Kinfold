# Model families known to be closed-weight. An agent registered under one of
# these families always has open_weights forced to false, regardless of what
# the caller claims.
CLOSED_MODEL_FAMILIES: frozenset[str] = frozenset(
    {"claude", "gpt", "openai", "gemini", "grok"}
)

GENESIS_PREV_HASH = "0" * 64

HANDLE_PATTERN = r"^[a-z0-9_-]{3,40}$"
