from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Claim, Entity


def search_entities(db: Session, user_id, q: str, entity_type: str | None, max_results: int) -> list[Entity]:
    query = db.query(Entity).filter(Entity.user_id == user_id)

    if entity_type:
        query = query.filter(Entity.type == entity_type)

    pattern = f"%{q}%"
    query = query.filter(
        or_(
            Entity.data["name"].astext.ilike(pattern),
            Entity.data["org"].astext.ilike(pattern),
        )
    )

    return query.order_by(Entity.updated_at.desc()).limit(max_results).all()


def find_or_create_entity(db: Session, user_id, entity_type: str, match: dict[str, Any]) -> Entity:
    query = db.query(Entity).filter(Entity.user_id == user_id, Entity.type == entity_type)
    if match:
        query = query.filter(Entity.data.contains(match))

    entity = query.order_by(Entity.updated_at.desc()).first()
    if entity:
        return entity

    entity = Entity(user_id=user_id, type=entity_type, data=dict(match))
    db.add(entity)
    db.flush()
    return entity


def write_with_claims(db: Session, user_id, client_id: str, entity: Entity, patch: dict[str, Any]):
    applied: list[str] = []
    proposed: list[dict[str, Any]] = []

    data = dict(entity.data or {})

    for field, new_value in patch.items():
        current_value = data.get(field)
        is_empty = field not in data or current_value is None or current_value == ""

        if is_empty:
            data[field] = new_value
            applied.append(field)
            claim = Claim(
                user_id=user_id,
                client_id=client_id,
                entity_id=entity.id,
                entity_type=entity.type,
                field=field,
                old_value=current_value,
                new_value=new_value,
                status="applied",
            )
            db.add(claim)
            continue

        if current_value != new_value:
            claim = Claim(
                user_id=user_id,
                client_id=client_id,
                entity_id=entity.id,
                entity_type=entity.type,
                field=field,
                old_value=current_value,
                new_value=new_value,
                status="proposed",
            )
            db.add(claim)
            db.flush()
            proposed.append(
                {
                    "field": field,
                    "claim_id": claim.id,
                    "current": current_value,
                    "new": new_value,
                }
            )

    entity.data = data
    entity.updated_at = datetime.now(timezone.utc)
    db.flush()

    return applied, proposed


def list_claims(db: Session, user_id, status: str) -> list[Claim]:
    return (
        db.query(Claim)
        .filter(Claim.user_id == user_id, Claim.status == status)
        .order_by(Claim.created_at.desc())
        .all()
    )


def confirm_claim(db: Session, user_id, claim_id):
    claim = db.query(Claim).filter(Claim.id == claim_id, Claim.user_id == user_id).first()
    if not claim:
        return None, "not_found"

    if claim.status != "proposed":
        return None, "invalid_status"

    entity = db.query(Entity).filter(Entity.id == claim.entity_id, Entity.user_id == user_id).first()
    if not entity:
        return None, "entity_not_found"

    data = dict(entity.data or {})
    data[claim.field] = claim.new_value
    entity.data = data
    entity.updated_at = datetime.now(timezone.utc)

    claim.status = "confirmed"
    claim.confirmed_at = datetime.now(timezone.utc)

    db.flush()
    return entity, None
