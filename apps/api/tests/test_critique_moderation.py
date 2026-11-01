"""20 example critiques (English + Hinglish, normal + personal attacks),
the same set used to audit the heuristic for docs/progress.md, 2026-11-01.
Locks in the fixes made that day so a future change can't silently
reopen the false positive or the misses."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from kinfold_api.services.critique_moderation import check_critique_text


def _is_blocked(text: str) -> bool:
    try:
        check_critique_text(text)
    except HTTPException:
        return True
    return False


NORMAL_ENGLISH = [
    "The code is inefficient and doesn't handle edge cases well.",
    "This explanation is clear but misses the time complexity analysis.",
    "The answer repeats itself and doesn't add new information in the second half.",
    "Good use of examples, but the conclusion is weak.",
    "This looks like it was rushed, several logical gaps in the argument.",
]

NORMAL_HINGLISH = [
    "Ye code bahut slow hai, time complexity better honi chahiye.",
    "Explanation theek hai lekin examples kam hain.",
    "Answer achha hai par thoda incomplete lagta hai.",
    "Logic sahi hai magar code readability improve ho sakti hai.",
    "Yeh jawab bohot generic hai, specific nahi hai.",
]

ATTACK_ENGLISH = [
    "This person is clearly an idiot who doesn't know basic math.",
    "Whoever wrote this probably grew up without proper education.",
    "The writer sounds foreign, English isn't their first language obviously.",
    "This looks ugly and the person who wrote it is probably not very bright.",
    "He is obviously a teenager who doesn't understand real-world coding.",
]

ATTACK_HINGLISH = [
    "Yeh insaan pakka gay hai, iska code bhi weird hai.",
    "Lagta hai yeh likhne wala Muslim hai, iska approach alag hai.",
    "Is writer ka accent clearly pata chal raha hai, foreigner lagta hai.",
    "Yeh banda pakka dumb hai, uska code dekh ke lagta hai.",
    "Uski family background kharab hai, isliye coding bhi weak hai.",
]


@pytest.mark.parametrize("text", NORMAL_ENGLISH + NORMAL_HINGLISH)
def test_normal_critiques_are_allowed(text):
    assert not _is_blocked(text), f"false positive: {text!r}"


@pytest.mark.parametrize("text", ATTACK_ENGLISH + ATTACK_HINGLISH)
def test_personal_attacks_are_blocked(text):
    assert _is_blocked(text), f"missed: {text!r}"
