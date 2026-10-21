from __future__ import annotations


def expected_score(rating_a: int, rating_b: int) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def elo_delta(rating_a: int, rating_b: int, *, score_a: float, k_factor: int) -> int:
    """score_a is 1.0 for a win, 0.0 for a loss, 0.5 for a draw."""
    return round(k_factor * (score_a - expected_score(rating_a, rating_b)))
