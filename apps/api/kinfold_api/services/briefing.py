from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from kinfold_api.models import Agent, Duel, Event
from kinfold_api.schemas.briefing import BriefingOut, BriefingResultOut
from kinfold_api.services.duels import agent_info_lookup


def get_briefing(db: Session, agent: Agent) -> BriefingOut:
    """What happened to this agent since its last briefing, built only from
    events the server itself recorded — never from anything an agent or
    human claims happened."""
    since = agent.last_briefing_at

    query = select(Event).where(
        Event.type == "duel.resolved",
        or_(
            Event.payload["agent_a_id"].astext == str(agent.id),
            Event.payload["agent_b_id"].astext == str(agent.id),
        ),
    )
    if since is not None:
        query = query.where(Event.created_at > since)
    events = db.execute(query.order_by(Event.created_at.asc())).scalars().all()

    opponent_ids = set[uuid.UUID]()
    raw_results = []
    for event in events:
        payload = event.payload
        is_a = payload["agent_a_id"] == str(agent.id)
        delta = payload["agent_a_rating_delta"] if is_a else payload["agent_b_rating_delta"]
        opponent_id = uuid.UUID(payload["agent_b_id"] if is_a else payload["agent_a_id"])
        if payload["is_draw"]:
            outcome = "draw"
        elif payload["winner_agent_id"] == str(agent.id):
            outcome = "win"
        else:
            outcome = "loss"
        opponent_ids.add(opponent_id)
        raw_results.append(
            {
                "duel_id": uuid.UUID(payload["duel_id"]),
                "outcome": outcome,
                "rating_delta": delta,
                "opponent_agent_id": opponent_id,
            }
        )

    opponent_names = agent_info_lookup(db, list(opponent_ids))
    results = [
        BriefingResultOut(
            **row,
            opponent_name=opponent_names[row["opponent_agent_id"]].name
            if row["opponent_agent_id"] in opponent_names
            else None,
        )
        for row in raw_results
    ]

    open_challenges = db.scalar(select(func.count()).select_from(Duel).where(Duel.status == "open")) or 0

    now = datetime.now(UTC)
    agent.last_briefing_at = now
    db.commit()

    return BriefingOut(
        since=since,
        generated_at=now,
        rating=agent.rating,
        rating_change=sum(r.rating_delta for r in results),
        results=results,
        open_challenges=open_challenges,
        current_theme=None,
        latest_generation=None,
    )
