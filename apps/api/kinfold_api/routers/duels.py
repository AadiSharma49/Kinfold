from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kinfold_api.constants import DUEL_CATEGORIES
from kinfold_api.db import get_db
from kinfold_api.deps import require_agent_key, require_owner_key
from kinfold_api.models import Agent, ApiKey, Duel, DuelEntry, Owner, Vote
from kinfold_api.schemas.duel import (
    DuelCreateRequest,
    DuelDetailOut,
    DuelEntryOut,
    DuelEntrySubmitRequest,
    DuelOut,
    VoteRequest,
)
from kinfold_api.schemas.judgment import JudgmentCreateRequest, JudgmentOut
from kinfold_api.services.duels import AgentInfo, agent_info_lookup, create_duel, submit_entry
from kinfold_api.services.judging import cast_agent_judgment, judgment_out_data, list_judgments
from kinfold_api.services.voting import cast_vote

router = APIRouter(tags=["duels"])


def _get_duel_or_404(db: Session, duel_id: uuid.UUID) -> Duel:
    duel = db.get(Duel, duel_id)
    if duel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return duel


def _entry_out(entry: DuelEntry, duel: Duel, infos: dict[uuid.UUID, AgentInfo]) -> DuelEntryOut:
    reveal = duel.status == "resolved"
    info = infos.get(entry.agent_id) if reveal else None
    return DuelEntryOut(
        id=entry.id,
        slot=entry.slot,
        answer=entry.answer,
        passed_tests=entry.passed_tests,
        total_tests=entry.total_tests,
        submitted_at=entry.submitted_at,
        agent_id=entry.agent_id if reveal else None,
        agent_name=info.name if info else None,
        agent_is_house=info.is_house if info else None,
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
    return DuelOut.model_validate(duel)


@router.get("/duels", response_model=list[DuelOut])
def list_duels(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[DuelOut]:
    query = select(Duel).order_by(Duel.created_at.desc())
    if status_filter is not None:
        query = query.where(Duel.status == status_filter)
    if category is not None:
        if category not in DUEL_CATEGORIES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"category must be one of {sorted(DUEL_CATEGORIES)}"
            )
        query = query.where(Duel.category == category)

    duels = db.execute(query).scalars().all()
    return [DuelOut.model_validate(d) for d in duels]


@router.get("/duels/{duel_id}", response_model=DuelDetailOut)
def get_duel(duel_id: uuid.UUID, db: Session = Depends(get_db)) -> DuelDetailOut:
    duel = _get_duel_or_404(db, duel_id)
    entries = (
        db.execute(select(DuelEntry).where(DuelEntry.duel_id == duel.id).order_by(DuelEntry.slot))
        .scalars()
        .all()
    )
    infos = agent_info_lookup(db, [e.agent_id for e in entries]) if duel.status == "resolved" else {}

    votes_cast = db.execute(
        select(func.count()).select_from(Vote).where(Vote.duel_id == duel.id)
    ).scalar_one()

    return DuelDetailOut(
        **DuelOut.model_validate(duel).model_dump(),
        entries=[_entry_out(e, duel, infos) for e in entries],
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
    return _entry_out(entry, duel, infos)


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
