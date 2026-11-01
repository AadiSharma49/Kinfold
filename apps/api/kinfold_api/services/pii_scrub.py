"""Scrubs obvious personal data and secrets out of text before it goes into
any exported dataset. A regex heuristic, not a guarantee — documented as a
known limitation, same honesty standard as the critique-moderation
heuristic (see docs/decisions.md, 2026-11-01). Catches the common,
unambiguous cases; doesn't claim to catch everything a determined bad
actor could slip past it.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Kinfold's own keys first — most specific, must not be caught by the
    # generic token pattern below and left half-redacted.
    (re.compile(r"\bkf_(owner|live)_[A-Za-z0-9_-]{10,}\b"), "[redacted-kinfold-key]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[redacted-email]"),
    (
        re.compile(r"(?<!\d)(\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"),
        "[redacted-phone]",
    ),
    # Common API-key/token shapes: long runs of base64url-ish characters,
    # or well-known prefixes (OpenAI, GitHub, AWS, Slack, Anthropic).
    (re.compile(r"\b(sk|pk)-[A-Za-z0-9]{16,}\b"), "[redacted-token]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[redacted-token]"),
    (re.compile(r"\bAKIA[A-Z0-9]{12,}\b"), "[redacted-token]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "[redacted-token]"),
]

# Deliberately not included: a generic "any long opaque string" pattern.
# It false-positives too often on legitimate long identifiers in code
# answers (hashes, UUIDs used as examples, etc.) — only the specific,
# high-confidence patterns above run.


def scrub_pii(text: str) -> str:
    """Applies every pattern above, in order."""
    result = text
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result
