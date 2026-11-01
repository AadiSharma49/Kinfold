from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kinfold_api.constants import DUEL_CATEGORIES
from kinfold_api.db import get_db
from kinfold_api.deps import require_agent_key, require_any_key, require_owner_key
from kinfold_api.models import Agent, ApiKey, Duel, DuelEntry, Owner, Vote
from kinfold_api.schemas.duel import (
    BugListingCreateRequest,
    DuelCreateRequest,
    DuelDetailOut,
    DuelEntryOut,
    DuelEntrySubmitRequest,
    DuelOut,
    HumanEntrySubmitRequest,
    VoteRequest,
)
from kinfold_api.schemas.judgment import (
    JudgmentCreateRequest,
    JudgmentOut,
    RateJudgmentUsefulRequest,
)
from kinfold_api.services.duels import (
    AgentInfo,
    agent_info_lookup,
    create_bug_listing,
    create_duel,
    owner_handle_lookup,
    submit_entry,
    submit_human_entry,
)
from kinfold_api.services.judging import (
    cast_agent_judgment,
    judgment_out_data,
    list_judgments,
    rate_judgment_useful,
)
from kinfold_api.services.voting import cast_vote

router = APIRouter(tags=["duels"])


def _get_duel_or_404(db: Session, duel_id: uuid.UUID) -> Duel:
    duel = db.get(Duel, duel_id)
    if duel is None or duel.hidden_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return duel


_REMOVED_ANSWER_NOTICE = "[removed by moderator]"


def _duel_out(duel: Duel, creator_handle: str | None = None) -> DuelOut:
    """Not model_validate(duel) — created_by_human_owner_handle isn't a
    column on Duel, it's resolved via owner_handle_lookup by the caller.
    Not blind: the lister never submits an entry, so there's no judging
    concern with showing it immediately."""
    return DuelOut(
        id=duel.id,
        category=duel.category,
        status=duel.status,
        prompt=duel.prompt,
        created_at=duel.created_at,
        resolved_at=duel.resolved_at,
        winner_agent_id=duel.winner_agent_id,
        winner_human_owner_id=duel.winner_human_owner_id,
        is_draw=duel.is_draw,
        created_by_human_owner_handle=creator_handle,
    )


def _entry_out(
    entry: DuelEntry,
    duel: Duel,
    infos: dict[uuid.UUID, AgentInfo],
    owner_handles: dict[uuid.UUID, str],
) -> DuelEntryOut:
    reveal = duel.status == "resolved"
    info = infos.get(entry.agent_id) if reveal and entry.agent_id else None
    owner_handle = owner_handles.get(entry.human_owner_id) if reveal and entry.human_owner_id else None
    answer = _REMOVED_ANSWER_NOTICE if entry.hidden_at is not None else entry.answer
    return DuelEntryOut(
        id=entry.id,
        slot=entry.slot,
        answer=answer,
        passed_tests=entry.passed_tests,
        total_tests=entry.total_tests,
        submitted_at=entry.submitted_at,
        agent_id=entry.agent_id if reveal else None,
        agent_name=info.name if info else None,
        agent_is_house=info.is_house if info else None,
        human_owner_handle=owner_handle,
        # Gated behind `reveal`, same as identity: a time-taken or declared
        # tools value present pre-resolution would itself leak which entry
        # is the human one, defeating blind judging.
        human_time_taken_seconds=entry.human_time_taken_seconds if reveal else None,
        human_declared_ai_tools=entry.human_declared_ai_tools if reveal else None,
        human_suspected_ai=entry.human_suspected_ai if reveal else None,
        human_suspected_ai_reasons=entry.human_suspected_ai_reasons if reveal else None,
    )


@router.post("/duels", response_model=DuelOut, status_code=status.HTTP_201_CREATED)
def create_duel_route(
    body: DuelCreateRequest,
    key: ApiKey = Depends(require_agent_key),
    db: Session = Depends(get_db),
) -> DuelOut:
    agent = db.get(Agent, key.agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    tests = [(t.input, t.expected_output) for t in body.tests]
    duel = create_duel(
        db,
        creator_agent=agent,
        category=body.category,
        prompt=body.prompt,
        answer=body.answer,
        tests=tests,
    )
    return _duel_out(duel)


@router.post("/listings", response_model=DuelOut, status_code=status.HTTP_201_CREATED)
def create_bug_listing_route(
    body: BugListingCreateRequest,
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> DuelOut:
    """"Bring a bug" — see docs/listings.md. A human lists a real bug;
    agents fix it via the usual POST /v1/duels/{id}/entries."""
    owner = db.get(Owner, key.owner_id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    tests = [(t.input, t.expected_output) for t in body.tests]
    duel = create_bug_listing(db, owner=owner, prompt=body.prompt, tests=tests)
    return _duel_out(duel, creator_handle=owner.handle)


@router.get("/duels", response_model=list[DuelOut])
def list_duels(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[DuelOut]:
    query = select(Duel).where(Duel.hidden_at.is_(None)).order_by(Duel.created_at.desc())
    if status_filter is not None:
        query = query.where(Duel.status == status_filter)
    if category is not None:
        if category not in DUEL_CATEGORIES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"category must be one of {sorted(DUEL_CATEGORIES)}"
            )
        query = query.where(Duel.category == category)

    duels = db.execute(query).scalars().all()
    creator_handles = owner_handle_lookup(db, [d.created_by_human_owner_id for d in duels])
    return [
        _duel_out(d, creator_handle=creator_handles.get(d.created_by_human_owner_id))
        for d in duels
    ]


@router.get("/duels/{duel_id}", response_model=DuelDetailOut)
def get_duel(duel_id: uuid.UUID, db: Session = Depends(get_db)) -> DuelDetailOut:
    duel = _get_duel_or_404(db, duel_id)
    entries = (
        db.execute(select(DuelEntry).where(DuelEntry.duel_id == duel.id).order_by(DuelEntry.slot))
        .scalars()
        .all()
    )
    reveal = duel.status == "resolved"
    infos = agent_info_lookup(db, [e.agent_id for e in entries]) if reveal else {}
    owner_handles = owner_handle_lookup(
        db, [e.human_owner_id for e in entries] + [duel.created_by_human_owner_id]
    )
    entry_owner_handles = owner_handles if reveal else {}

    votes_cast = db.execute(
        select(func.count()).select_from(Vote).where(Vote.duel_id == duel.id)
    ).scalar_one()

    return DuelDetailOut(
        **_duel_out(
            duel, creator_handle=owner_handles.get(duel.created_by_human_owner_id)
        ).model_dump(),
        entries=[_entry_out(e, duel, infos, entry_owner_handles) for e in entries],
        votes_cast=votes_cast,
    )


@router.post("/duels/{duel_id}/entries", response_model=DuelEntryOut, status_code=status.HTTP_201_CREATED)
def submit_entry_route(
    duel_id: uuid.UUID,
    body: DuelEntrySubmitRequest,
    key: ApiKey = Depends(require_agent_key),
    db: Session = Depends(get_db),
) -> DuelEntryOut:
    agent = db.get(Agent, key.agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    duel = _get_duel_or_404(db, duel_id)
    entry = submit_entry(db, duel=duel, agent=agent, answer=body.answer)
    db.refresh(duel)
    infos = agent_info_lookup(db, [entry.agent_id]) if duel.status == "resolved" else {}
    return _entry_out(entry, duel, infos, {})


@router.post(
    "/duels/{duel_id}/human-entry", response_model=DuelEntryOut, status_code=status.HTTP_201_CREATED
)
def submit_human_entry_route(
    duel_id: uuid.UUID,
    body: HumanEntrySubmitRequest,
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> DuelEntryOut:
    owner = db.get(Owner, key.owner_id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    duel = _get_duel_or_404(db, duel_id)
    entry = submit_human_entry(
        db,
        duel=duel,
        owner=owner,
        answer=body.answer,
        time_taken_seconds=body.time_taken_seconds,
        declared_ai_tools=body.declared_ai_tools,
        large_paste_detected=body.large_paste_detected,
    )
    db.refresh(duel)
    owner_handles = owner_handle_lookup(db, [entry.human_owner_id]) if duel.status == "resolved" else {}
    return _entry_out(entry, duel, {}, owner_handles)


@router.post("/duels/{duel_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
def vote_route(
    duel_id: uuid.UUID,
    body: VoteRequest,
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> None:
    owner = db.get(Owner, key.owner_id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    duel = _get_duel_or_404(db, duel_id)
    cast_vote(db, duel=duel, voter=owner, entry_id=body.entry_id)


@router.post(
    "/duels/{duel_id}/judgments", response_model=JudgmentOut, status_code=status.HTTP_201_CREATED
)
def judge_duel_route(
    duel_id: uuid.UUID,
    body: JudgmentCreateRequest,
    key: ApiKey = Depends(require_agent_key),
    db: Session = Depends(get_db),
) -> JudgmentOut:
    judge = db.get(Agent, key.agent_id)
    if judge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    duel = _get_duel_or_404(db, duel_id)
    judgment = cast_agent_judgment(
        db,
        duel=duel,
        judge=judge,
        entry_id=body.entry_id,
        strengths=body.strengths,
        weaknesses=body.weaknesses,
        verdict=body.verdict,
        score=body.score,
    )
    data = judgment_out_data(db, duel, [judgment])[0]
    return JudgmentOut(**data)


@router.get("/duels/{duel_id}/judgments", response_model=list[JudgmentOut])
def list_judgments_route(duel_id: uuid.UUID, db: Session = Depends(get_db)) -> list[JudgmentOut]:
    duel = _get_duel_or_404(db, duel_id)
    judgments = list_judgments(db, duel)
    return [JudgmentOut(**data) for data in judgment_out_data(db, duel, judgments)]


@router.post("/judgments/{judgment_id}/useful", response_model=JudgmentOut)
def rate_judgment_useful_route(
    judgment_id: uuid.UUID,
    body: RateJudgmentUsefulRequest,
    key: ApiKey = Depends(require_any_key),
    db: Session = Depends(get_db),
) -> JudgmentOut:
    judgment = db.get(Vote, judgment_id)
    if judgment is None or judgment.voter_type != "agent":
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    rate_judgment_useful(
        db,
        judgment=judgment,
        rating_agent_id=key.agent_id,
        rating_owner_id=key.owner_id if key.kind == "owner" else None,
        useful=body.useful,
    )

    duel = db.get(Duel, judgment.duel_id)
    data = judgment_out_data(db, duel, [judgment])[0]
    return JudgmentOut(**data)
