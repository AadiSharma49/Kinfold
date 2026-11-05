from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.constants import CROWD_CATEGORIES, VERIFIED_CATEGORIES
from kinfold_api.models import Agent, CategoryRating, Duel, DuelEntry, DuelTest, Owner
from kinfold_api.services.events import append_event
from kinfold_api.services.rating import elo_delta
from kinfold_api.services.receipts import ReceiptIn, compute_latency_ms
from kinfold_api.services.sandbox import SandboxUnavailableError, run_python_tests

# Humans now have a real rating (Owner.rating) — see docs/decisions.md,
# 2026-11-02, which supersedes the fixed stand-in this used to be. Kept
# only as the defensive fallback in apply_resolution for an entry with
# neither an agent nor an owner, which the DB's own entrant-kind check
# constraint should never actually allow.
HUMAN_VIRTUAL_RATING = 1200


def _ensure_agent_active(agent: Agent) -> None:
    """A disabled agent (an admin action, usually in response to a report)
    can't create or join duels. See docs/decisions.md, 2026-10-31."""
    if agent.is_disabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This agent has been disabled.")


def _ensure_test_cap(tests: list[tuple[str, str]]) -> None:
    """Each hidden test is run in a fresh sandbox container, so the creator
    supplied list is capped — see KINFOLD_MAX_TESTS_PER_DUEL."""
    limit = get_settings().KINFOLD_MAX_TESTS_PER_DUEL
    if len(tests) > limit:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"A duel can have at most {limit} hidden tests.",
        )


def _ensure_sandbox_access(agent: Agent) -> None:
    """Code-duel answers run in the sandbox, which is still DooD (the API
    process holds the host's Docker socket) until gVisor replaces it — see
    docs/decisions.md, 2026-10-29. While KINFOLD_SANDBOX_RESTRICTED is on,
    only house agents and agents approved via scripts/approve_sandbox_agent.py
    can submit code-duel answers at all."""
    if not get_settings().KINFOLD_SANDBOX_RESTRICTED:
        return
    if agent.is_house or agent.sandbox_approved:
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Code duels are restricted to approved agents right now. "
        "See docs/decisions.md for why, and ask the operator for approval.",
    )


def create_duel(
    db: Session,
    *,
    creator_agent: Agent,
    category: str,
    prompt: str,
    answer: str,
    tests: list[tuple[str, str]],
    receipt: ReceiptIn | None = None,
) -> Duel:
    _ensure_agent_active(creator_agent)
    if category in VERIFIED_CATEGORIES:
        _ensure_sandbox_access(creator_agent)
        _ensure_test_cap(tests)
    receipt = receipt or ReceiptIn()

    duel = Duel(
        category=category,
        status="open",
        prompt=prompt,
        created_by_agent_id=creator_agent.id,
    )
    db.add(duel)
    db.flush()

    entry = DuelEntry(
        duel_id=duel.id,
        agent_id=creator_agent.id,
        slot=1,
        answer=answer,
        receipt_tokens_in=receipt.tokens_in,
        receipt_tokens_out=receipt.tokens_out,
        receipt_tool_calls=receipt.tool_calls,
        receipt_autonomous=receipt.autonomous,
        receipt_latency_ms=compute_latency_ms(receipt.started_at),
    )
    db.add(entry)

    if category in VERIFIED_CATEGORIES:
        for index, (test_input, expected_output) in enumerate(tests):
            db.add(
                DuelTest(
                    duel_id=duel.id,
                    order_index=index,
                    input=test_input,
                    expected_output=expected_output,
                )
            )

    db.flush()
    append_event(
        db,
        type="duel.created",
        agent_id=creator_agent.id,
        owner_id=creator_agent.owner_id,
        payload={"duel_id": str(duel.id), "category": category},
    )
    db.commit()
    db.refresh(duel)
    return duel


def create_bug_listing(
    db: Session, *, owner: Owner, prompt: str, tests: list[tuple[str, str]]
) -> Duel:
    """"Bring a bug" (see docs/bring-a-bug.md): a human lists a real bug —
    prompt is the description/repro steps, tests are the hidden test
    case(s) that currently fail. No entry is created here; two agents
    submit competing fixes via submit_entry, same hidden-test judging as
    a "code" duel. The listing owner never enters their own listing."""
    _ensure_test_cap(tests)
    duel = Duel(
        category="bugfix",
        status="open",
        prompt=prompt,
        created_by_human_owner_id=owner.id,
    )
    db.add(duel)
    db.flush()

    for index, (test_input, expected_output) in enumerate(tests):
        db.add(
            DuelTest(
                duel_id=duel.id,
                order_index=index,
                input=test_input,
                expected_output=expected_output,
            )
        )

    db.flush()
    append_event(
        db,
        type="listing.created",
        owner_id=owner.id,
        payload={"duel_id": str(duel.id)},
    )
    db.commit()
    db.refresh(duel)
    return duel


def _submit_bugfix_entry(
    db: Session, *, duel: Duel, agent: Agent, answer: str, receipt: ReceiptIn
) -> DuelEntry:
    """Bug listings have no first-entrant creator answer to compare
    against — both slots are filled by competing agent fixes, first come
    first served. Resolution (hidden tests, Elo) is identical to a "code"
    duel once both slots are filled — see resolve_verified_duel."""
    if agent.owner_id == duel.created_by_human_owner_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Can't submit a fix to your own bug listing.")
    _ensure_sandbox_access(agent)

    existing = db.execute(
        select(DuelEntry).where(DuelEntry.duel_id == duel.id)
    ).scalars().all()
    if any(e.agent_id == agent.id for e in existing):
        raise HTTPException(status.HTTP_409_CONFLICT, "This agent already submitted a fix.")
    # Two agents run by the same owner must not fill both sides of a
    # listing — otherwise one owner controls the result and can farm Elo.
    sibling = db.execute(
        select(DuelEntry.id)
        .join(Agent, Agent.id == DuelEntry.agent_id)
        .where(DuelEntry.duel_id == duel.id, Agent.owner_id == agent.owner_id)
    ).first()
    if sibling is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Agents run by the same owner can't compete in the same listing.",
        )
    taken_slots = {e.slot for e in existing}
    if 1 not in taken_slots:
        slot = 1
    elif 2 not in taken_slots:
        slot = 2
    else:
        raise HTTPException(status.HTTP_409_CONFLICT, "This listing already has two fixes submitted.")

    entry = DuelEntry(
        duel_id=duel.id,
        agent_id=agent.id,
        slot=slot,
        answer=answer,
        receipt_tokens_in=receipt.tokens_in,
        receipt_tokens_out=receipt.tokens_out,
        receipt_tool_calls=receipt.tool_calls,
        receipt_autonomous=receipt.autonomous,
        receipt_latency_ms=compute_latency_ms(receipt.started_at),
    )
    db.add(entry)
    if slot == 2:
        duel.status = "judging"
        duel.judging_started_at = datetime.now(UTC)
    db.flush()

    append_event(
        db,
        type="duel.entry_submitted",
        agent_id=agent.id,
        owner_id=agent.owner_id,
        payload={"duel_id": str(duel.id), "slot": slot},
    )
    db.commit()
    db.refresh(entry)

    if slot == 2:
        resolve_verified_duel(db, duel)
        db.refresh(entry)
    return entry


def submit_entry(
    db: Session,
    *,
    duel: Duel,
    agent: Agent,
    answer: str,
    is_trap: bool = False,
    receipt: ReceiptIn | None = None,
) -> DuelEntry:
    """is_trap is never reachable from the public submit-entry endpoint —
    only scripts/plant_trap_entry.py calls this with it set, the same
    pattern as is_house and sandbox_approved. A trap entry is a real entry
    in every other way (judged, voted on, revealed once resolved); it's
    just internally known to be deliberately bad, for checking whether
    judges actually discriminate quality."""
    _ensure_agent_active(agent)
    # Serialize joins on one duel. Without this, two agents could both see
    # "open" and race for slot 2 (the unique constraint would turn the
    # loser into a 500 instead of a clean 409).
    duel = db.execute(select(Duel).where(Duel.id == duel.id).with_for_update()).scalar_one()
    if duel.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This duel is no longer open for entries.")
    receipt = receipt or ReceiptIn()

    if duel.category == "bugfix":
        if is_trap:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Trap entries aren't supported for bugfix listings."
            )
        return _submit_bugfix_entry(db, duel=duel, agent=agent, answer=answer, receipt=receipt)

    if agent.id == duel.created_by_agent_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "An agent can't duel itself.")
    creator = db.get(Agent, duel.created_by_agent_id)
    if creator is not None and creator.owner_id == agent.owner_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Agents run by the same owner can't duel each other.",
        )
    if duel.category in VERIFIED_CATEGORIES:
        _ensure_sandbox_access(agent)

    entry = DuelEntry(
        duel_id=duel.id,
        agent_id=agent.id,
        slot=2,
        answer=answer,
        is_trap=is_trap,
        receipt_tokens_in=receipt.tokens_in,
        receipt_tokens_out=receipt.tokens_out,
        receipt_tool_calls=receipt.tool_calls,
        receipt_autonomous=receipt.autonomous,
        receipt_latency_ms=compute_latency_ms(receipt.started_at),
    )
    db.add(entry)
    duel.status = "judging"
    duel.judging_started_at = datetime.now(UTC)
    db.flush()

    append_event(
        db,
        type="duel.entry_submitted",
        agent_id=agent.id,
        owner_id=agent.owner_id,
        payload={"duel_id": str(duel.id)},
    )
    db.commit()
    db.refresh(entry)

    if duel.category in VERIFIED_CATEGORIES:
        resolve_verified_duel(db, duel)

    db.refresh(entry)
    return entry


# Simple, documented heuristics — not a verdict. We cannot prove humanity,
# so a flagged entry stays on the ladder and is judged normally; it is only
# excluded from the "human" side of the dataset export. See
# docs/decisions.md, 2026-11-01.
_SUSPICIOUSLY_FAST_CHARS_PER_SECOND = 14
_SUSPICIOUSLY_FAST_MIN_ANSWER_LENGTH = 200
_INSTANT_SUBMIT_MIN_ANSWER_LENGTH = 50


def _detect_suspected_ai(
    answer: str, time_taken_seconds: int | None, large_paste_detected: bool
) -> tuple[bool, str | None]:
    """Returns (suspected, reasons). Two signals, combined:
    1. The answer is long but was typed faster than a human plausibly
       types sustained prose/code (chars/second over a length threshold, so
       a short quick answer doesn't trip it).
    2. A single paste event inserted a large chunk of the final answer —
       reported by the client, see schemas/duel.py."""
    reasons: list[str] = []

    if time_taken_seconds is not None and len(answer) >= _INSTANT_SUBMIT_MIN_ANSWER_LENGTH:
        if time_taken_seconds <= 0:
            reasons.append("submitted instantly for a non-trivial answer length")
        elif (
            len(answer) >= _SUSPICIOUSLY_FAST_MIN_ANSWER_LENGTH
            and len(answer) / time_taken_seconds > _SUSPICIOUSLY_FAST_CHARS_PER_SECOND
        ):
            reasons.append("answer length vs. time taken is far faster than typical typing speed")

    if large_paste_detected:
        reasons.append("a large chunk of the answer was pasted in a single action")

    return (len(reasons) > 0, "; ".join(reasons) if reasons else None)


def submit_human_entry(
    db: Session,
    *,
    duel: Duel,
    owner: Owner,
    answer: str,
    time_taken_seconds: int | None = None,
    declared_ai_tools: str | None = None,
    large_paste_detected: bool = False,
) -> DuelEntry:
    """A signed-in human joins an open crowd duel with their own answer —
    "Can you beat the AI?" Judged on the exact same blind-vote ladder as
    an agent entry would be. Code duels aren't open to this (there's no
    hidden-test judging path for a human's own prose about their code, and
    the sandbox restriction is about agents specifically) — only crowd
    categories, for now.

    time_taken_seconds and declared_ai_tools are the human's receipt —
    self-reported, same as the answer text itself, never verified."""
    if duel.category not in CROWD_CATEGORIES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only crowd duels are open to a human entry.")
    duel = db.execute(select(Duel).where(Duel.id == duel.id).with_for_update()).scalar_one()
    if duel.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This duel is no longer open for entries.")

    creator = db.get(Agent, duel.created_by_agent_id)
    if creator is not None and creator.owner_id == owner.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Can't enter a duel one of your own agents created."
        )

    suspected_ai, suspected_ai_reasons = _detect_suspected_ai(
        answer, time_taken_seconds, large_paste_detected
    )
    entry = DuelEntry(
        duel_id=duel.id,
        human_owner_id=owner.id,
        slot=2,
        answer=answer,
        human_time_taken_seconds=time_taken_seconds,
        human_declared_ai_tools=declared_ai_tools,
        human_large_paste_detected=large_paste_detected,
        human_suspected_ai=suspected_ai,
        human_suspected_ai_reasons=suspected_ai_reasons,
    )
    db.add(entry)
    duel.status = "judging"
    duel.judging_started_at = datetime.now(UTC)
    db.flush()

    append_event(
        db,
        type="duel.entry_submitted",
        owner_id=owner.id,
        payload={"duel_id": str(duel.id), "entrant_kind": "human"},
    )
    db.commit()
    db.refresh(entry)
    return entry


def resolve_verified_duel(db: Session, duel: Duel) -> None:
    entries = db.execute(
        select(DuelEntry).where(DuelEntry.duel_id == duel.id).order_by(DuelEntry.slot)
    ).scalars().all()
    if len(entries) != 2:
        return

    tests = db.execute(
        select(DuelTest).where(DuelTest.duel_id == duel.id).order_by(DuelTest.order_index)
    ).scalars().all()
    test_pairs = [(t.input, t.expected_output) for t in tests]

    try:
        for entry in entries:
            result = run_python_tests(entry.answer, test_pairs)
            entry.passed_tests = result.passed_tests
            entry.total_tests = result.total_tests
    except SandboxUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The code sandbox is unavailable right now. Try again shortly.",
        ) from exc

    db.flush()

    entry_a, entry_b = entries
    if entry_a.passed_tests == entry_b.passed_tests:
        apply_resolution(db, duel, entry_a, entry_b, winner_entry=None)
    elif (entry_a.passed_tests or 0) > (entry_b.passed_tests or 0):
        apply_resolution(db, duel, entry_a, entry_b, winner_entry=entry_a)
    else:
        apply_resolution(db, duel, entry_a, entry_b, winner_entry=entry_b)


def _record_outcome(entity, score: float) -> None:
    """entity is an Agent, Owner, or CategoryRating — all three share the
    same wins/losses/draws attribute names on purpose, so this one helper
    works for every rating this module tracks."""
    if score == 1.0:
        entity.wins += 1
    elif score == 0.0:
        entity.losses += 1
    else:
        entity.draws += 1


def _reverse_outcome(entity, score: float | None) -> None:
    """Undo one _record_outcome call. Floors at zero so a double hide (or a
    legacy row without bookkeeping) can never make a record negative."""
    if score is None:
        return
    if score == 1.0:
        entity.wins = max(0, entity.wins - 1)
    elif score == 0.0:
        entity.losses = max(0, entity.losses - 1)
    else:
        entity.draws = max(0, entity.draws - 1)


def void_duel_ratings(db: Session, *, duel: Duel) -> bool:
    """Reverse every rating and record change a settled duel made, because
    one of its entries has been hidden by a moderator. Returns True if this
    call did the reversal, False if there was nothing to reverse or it was
    already done.

    The reversal is exact: apply_resolution stored each side's overall
    delta, category delta, and outcome on the entry itself, so this never
    has to recreate elo math from current (possibly moved) ratings. The
    change is recorded as a new event; the original duel.resolved event is
    never edited, so the append-only log keeps both facts.

    Public profiles and the dataset export omit duels with
    ratings_voided_at set, so a hidden entry cannot keep affecting stats.
    """
    if duel.status != "resolved" or duel.ratings_voided_at is not None:
        return False

    entries = db.execute(
        select(DuelEntry).where(DuelEntry.duel_id == duel.id)
    ).scalars().all()

    for entry in entries:
        if entry.rating_delta is None:
            continue
        agent = db.get(Agent, entry.agent_id) if entry.agent_id else None
        owner = db.get(Owner, entry.human_owner_id) if entry.human_owner_id else None
        side = agent or owner
        if side is not None:
            side.rating -= entry.rating_delta
            _reverse_outcome(side, entry.outcome_score)
        if entry.category_rating_delta is not None:
            cat = _get_or_create_category_rating(
                db,
                agent_id=agent.id if agent else None,
                human_owner_id=owner.id if owner else None,
                category=duel.category,
            )
            cat.rating -= entry.category_rating_delta
            _reverse_outcome(cat, entry.outcome_score)

    duel.ratings_voided_at = datetime.now(UTC)
    db.flush()
    append_event(
        db,
        type="duel.ratings_voided",
        agent_id=None,
        owner_id=None,
        payload={"duel_id": str(duel.id), "category": duel.category},
    )
    return True


def _get_or_create_category_rating(
    db: Session, *, agent_id: uuid.UUID | None, human_owner_id: uuid.UUID | None, category: str
) -> CategoryRating:
    query = select(CategoryRating).where(CategoryRating.category == category)
    query = query.where(
        CategoryRating.agent_id == agent_id
        if agent_id is not None
        else CategoryRating.human_owner_id == human_owner_id
    )
    row = db.execute(query).scalar_one_or_none()
    if row is None:
        row = CategoryRating(agent_id=agent_id, human_owner_id=human_owner_id, category=category)
        db.add(row)
        db.flush()
    return row


def apply_resolution(
    db: Session,
    duel: Duel,
    entry_a: DuelEntry,
    entry_b: DuelEntry,
    *,
    winner_entry: DuelEntry | None,
) -> None:
    """Resolves a duel between any mix of agent and human entries. Updates
    two independent ratings per side: one overall (Agent.rating /
    Owner.rating) and one for this duel's specific category
    (CategoryRating) — both elo, both using the same K-factor, neither
    derived from the other. Humans get a real rating here, not the old
    fixed HUMAN_VIRTUAL_RATING stand-in — see docs/decisions.md,
    2026-11-02 (supersedes 2026-10-31)."""
    # Only a duel that is actually awaiting a result may be resolved, and
    # the check must see committed state from other transactions. Lock the
    # row and re-read it here, at the point where the result is applied:
    # two crowd votes crossing the threshold, or an admin retry racing a
    # submission, both reach this function. The second call waits for the
    # lock, sees "resolved", and changes nothing.
    duel = db.execute(select(Duel).where(Duel.id == duel.id).with_for_update()).scalar_one()
    if duel.status != "judging":
        return
    # A hidden entry (admin moderation) must not move ratings. If a
    # moderator hid an entry before the duel resolved, leave the duel
    # unresolved rather than inventing a result from content that was
    # removed. A post-resolution hide is reversed exactly by
    # void_duel_ratings below.
    if entry_a.hidden_at is not None or entry_b.hidden_at is not None:
        return
    if duel.ratings_voided_at is not None:
        return

    settings = get_settings()
    agent_a = db.get(Agent, entry_a.agent_id) if entry_a.agent_id else None
    agent_b = db.get(Agent, entry_b.agent_id) if entry_b.agent_id else None
    owner_a = db.get(Owner, entry_a.human_owner_id) if entry_a.human_owner_id else None
    owner_b = db.get(Owner, entry_b.human_owner_id) if entry_b.human_owner_id else None
    if agent_a is None and agent_b is None:
        return  # shouldn't happen — a duel is always created by an agent

    side_a = agent_a or owner_a
    side_b = agent_b or owner_b
    rating_a = side_a.rating if side_a else HUMAN_VIRTUAL_RATING
    rating_b = side_b.rating if side_b else HUMAN_VIRTUAL_RATING

    if winner_entry is None:
        score_a = 0.5
    elif winner_entry is entry_a:
        score_a = 1.0
    else:
        score_a = 0.0
    score_b = 1.0 - score_a

    k_factor = settings.KINFOLD_ELO_K_FACTOR
    delta_a = elo_delta(rating_a, rating_b, score_a=score_a, k_factor=k_factor)
    delta_b = elo_delta(rating_b, rating_a, score_a=score_b, k_factor=k_factor)

    if side_a:
        side_a.rating += delta_a
        _record_outcome(side_a, score_a)
    if side_b:
        side_b.rating += delta_b
        _record_outcome(side_b, score_b)

    # Remember exactly what was applied so an admin hiding this entry
    # later can reverse it without guessing — see void_duel_ratings.
    entry_a.rating_delta = delta_a
    entry_a.outcome_score = score_a
    entry_b.rating_delta = delta_b
    entry_b.outcome_score = score_b

    # The per-category rating is a second, independent elo run — its own
    # ratings in, its own deltas out. A side with no overall rating here
    # (shouldn't happen — every entry is either an agent or a human owner)
    # simply gets no category rating either.
    if side_a and side_b:
        cat_a = _get_or_create_category_rating(
            db,
            agent_id=agent_a.id if agent_a else None,
            human_owner_id=owner_a.id if owner_a else None,
            category=duel.category,
        )
        cat_b = _get_or_create_category_rating(
            db,
            agent_id=agent_b.id if agent_b else None,
            human_owner_id=owner_b.id if owner_b else None,
            category=duel.category,
        )
        cat_delta_a = elo_delta(cat_a.rating, cat_b.rating, score_a=score_a, k_factor=k_factor)
        cat_delta_b = elo_delta(cat_b.rating, cat_a.rating, score_a=score_b, k_factor=k_factor)
        cat_a.rating += cat_delta_a
        cat_b.rating += cat_delta_b
        _record_outcome(cat_a, score_a)
        _record_outcome(cat_b, score_b)
        entry_a.category_rating_delta = cat_delta_a
        entry_b.category_rating_delta = cat_delta_b

    if winner_entry is None:
        duel.is_draw = True
    elif winner_entry is entry_a:
        duel.winner_agent_id = agent_a.id if agent_a else None
        duel.winner_human_owner_id = entry_a.human_owner_id
    else:
        duel.winner_agent_id = agent_b.id if agent_b else None
        duel.winner_human_owner_id = entry_b.human_owner_id

    duel.status = "resolved"
    duel.resolved_at = datetime.now(UTC)
    db.flush()

    # Deferred import: services/judging.py imports agent_info_lookup from
    # this module, so importing it at module load would be circular.
    from kinfold_api.services.judging import score_judgments_against_result

    score_judgments_against_result(db, duel)

    append_event(
        db,
        type="duel.resolved",
        agent_id=None,
        owner_id=None,
        payload={
            "duel_id": str(duel.id),
            "is_draw": duel.is_draw,
            "winner_agent_id": str(duel.winner_agent_id) if duel.winner_agent_id else None,
            "winner_human_owner_id": (
                str(duel.winner_human_owner_id) if duel.winner_human_owner_id else None
            ),
            "agent_a_id": str(agent_a.id) if agent_a else None,
            "agent_a_rating_delta": delta_a,
            "agent_b_id": str(agent_b.id) if agent_b else None,
            "agent_b_rating_delta": delta_b,
            "human_a_owner_id": str(owner_a.id) if owner_a else None,
            "human_a_rating_delta": delta_a if owner_a else None,
            "human_b_owner_id": str(owner_b.id) if owner_b else None,
            "human_b_rating_delta": delta_b if owner_b else None,
            "category": duel.category,
        },
    )
    db.commit()


def expire_stale_duels(db: Session) -> int:
    """Move duels that have been judging for too long to "expired".

    No rating change: an expiry is not a result, it just stops the ladder
    waiting forever on a dead sandbox or a vote threshold that will never
    be reached. Admins can reset and retry an expired duel. Uses
    skip_locked so two readers can expire different rows without queueing
    behind each other."""
    cutoff = datetime.now(UTC) - timedelta(minutes=get_settings().KINFOLD_DUEL_EXPIRY_MINUTES)
    duels = db.execute(
        select(Duel)
        .where(
            Duel.status == "judging",
            func.coalesce(Duel.judging_started_at, Duel.created_at) < cutoff,
        )
        .with_for_update(skip_locked=True)
    ).scalars().all()
    if not duels:
        return 0

    now = datetime.now(UTC)
    for duel in duels:
        duel.status = "expired"
        duel.expired_at = now
        append_event(
            db,
            type="duel.expired",
            agent_id=None,
            owner_id=None,
            payload={"duel_id": str(duel.id)},
        )
    db.commit()
    return len(duels)


def winning_entry_id(duel: Duel, entries: list[DuelEntry]) -> uuid.UUID | None:
    """The id of whichever entry actually won — agent or human — or None
    for a draw or an unresolved duel. Shared by judging.py so judge-rating
    scoring and the judgments API work the same regardless of who won."""
    if duel.is_draw:
        return None
    if duel.winner_agent_id is not None:
        return next((e.id for e in entries if e.agent_id == duel.winner_agent_id), None)
    if duel.winner_human_owner_id is not None:
        return next((e.id for e in entries if e.human_owner_id == duel.winner_human_owner_id), None)
    return None


class AgentInfo(NamedTuple):
    name: str
    is_house: bool
    model_name: str


def agent_info_lookup(db: Session, agent_ids: list[uuid.UUID | None]) -> dict[uuid.UUID, AgentInfo]:
    ids = [i for i in agent_ids if i is not None]
    if not ids:
        return {}
    rows = db.execute(
        select(Agent.id, Agent.name, Agent.is_house, Agent.model_name).where(Agent.id.in_(ids))
    ).all()
    return {
        row.id: AgentInfo(name=row.name, is_house=row.is_house, model_name=row.model_name)
        for row in rows
    }


def owner_handle_lookup(db: Session, owner_ids: list[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    ids = [i for i in owner_ids if i is not None]
    if not ids:
        return {}
    rows = db.execute(select(Owner.id, Owner.handle).where(Owner.id.in_(ids))).all()
    return {row.id: row.handle for row in rows}
