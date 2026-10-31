"""Enforces "judge the work, never the person" on agent critique text.

This is a keyword heuristic, not real NLP moderation — a known, documented
limitation (see docs/decisions.md, 2026-10-31), not a claim of full
coverage. It catches the obvious, blunt cases (a direct comment on
appearance, identity, religion, background, or personal life) without
pretending to catch every way a critique could cross that line. Real
language-model-based moderation is a reasonable next step, not built here.
"""

from __future__ import annotations

import re

from fastapi import HTTPException, status

# Deliberately blunt and over-inclusive in spirit, not exhaustive — these
# are categories, not a complete list of every possible phrase.
_BLOCKED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\blooks? (like|ugly|stupid|dumb)\b",
        r"\b(ugly|hideous|fat|skinny)\b",
        r"\b(he|she|they)('s| is| are) (probably|clearly|obviously) (a|an)\b",
        r"\b(race|racist|ethnicity|skin color)\b",
        r"\b(gay|straight|trans|sexuality|sexual orientation)\b",
        r"\b(muslim|christian|hindu|jewish|atheist|religion|religious)\b",
        r"\b(immigrant|foreigner|accent)\b",
        r"\bprobably (lives?|grew up)\b",
        r"\b(his|her|their) (family|childhood|upbringing|personal life)\b",
    ]
]


def check_critique_text(*texts: str) -> None:
    """Raises 400 if any piece of critique text matches a blocked
    pattern. Call this on every free-text field a judgment submits."""
    for text in texts:
        for pattern in _BLOCKED_PATTERNS:
            if pattern.search(text):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Judge the work, not the person — this critique reads like a comment "
                    "about who might have written the answer, not the answer itself.",
                )
