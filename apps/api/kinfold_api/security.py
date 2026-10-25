import hashlib
import secrets

OWNER_KEY_PREFIX = "kf_owner_"
AGENT_KEY_PREFIX = "kf_live_"

# Long enough to recognize a key in a list without helping reconstruct it.
DISPLAY_PREFIX_LENGTH = 12


def _generate_raw_key(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(32)}"


def generate_owner_key() -> str:
    return _generate_raw_key(OWNER_KEY_PREFIX)


def generate_agent_key() -> str:
    return _generate_raw_key(AGENT_KEY_PREFIX)


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def display_prefix(raw_key: str) -> str:
    return raw_key[:DISPLAY_PREFIX_LENGTH]
