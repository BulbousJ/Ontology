import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import crud
from app.auth import require_grant
from app.db import Base, engine, get_db
from app.models import Grant
from app.schemas import (
    ClaimOut,
    EntityOut,
    GrantCreateRequest,
    GrantCreateResponse,
    QueryRequest,
    WriteRequest,
    WriteResponse,
)

app = FastAPI(title="Ontology Vault")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.post("/dev/grants", response_model=GrantCreateResponse)
def create_dev_grant(payload: GrantCreateRequest, db: Session = Depends(get_db)):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    grant = Grant(
        user_id=payload.user_id,
        client_id=payload.client_id,
        scopes=payload.scopes,
        token=token,
        expires_at=expires_at,
    )
    db.add(grant)
    db.commit()

    return GrantCreateResponse(token=token, expires_at=expires_at)


@app.post("/query", response_model=list[EntityOut])
def query_entities(
    payload: QueryRequest,
    request: Request,
    db: Session = Depends(get_db),
    _grant=Depends(require_grant),
):
    entities = crud.search_entities(
        db=db,
        user_id=request.state.user_id,
        q=payload.q,
        entity_type=payload.entity_type,
        max_results=payload.max_results,
    )
    return [EntityOut(id=e.id, type=e.type, data=e.data) for e in entities]


@app.post("/write", response_model=WriteResponse)
def write_entity(
    payload: WriteRequest,
    request: Request,
    db: Session = Depends(get_db),
    _grant=Depends(require_grant),
):
    entity = crud.find_or_create_entity(
        db=db,
        user_id=request.state.user_id,
        entity_type=payload.entity_type,
        match=payload.match,
    )
    applied, proposed = crud.write_with_claims(
        db=db,
        user_id=request.state.user_id,
        client_id=request.state.client_id,
        entity=entity,
        patch=payload.patch,
    )
    db.commit()
    return WriteResponse(entity_id=entity.id, applied=applied, proposed=proposed)


@app.get("/claims", response_model=list[ClaimOut])
def get_claims(
    request: Request,
    status_filter: Literal["proposed", "applied", "confirmed"] = "proposed",
    db: Session = Depends(get_db),
    _grant=Depends(require_grant),
):
    claims = crud.list_claims(db=db, user_id=request.state.user_id, status=status_filter)
    return [ClaimOut.model_validate(c) for c in claims]


@app.post("/claims/{claim_id}/confirm", response_model=EntityOut)
def confirm_claim(
    claim_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    _grant=Depends(require_grant),
):
    entity, error = crud.confirm_claim(db=db, user_id=request.state.user_id, claim_id=claim_id)
    if error == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    if error == "invalid_status":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Claim is not in proposed state")
    if error == "entity_not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    db.commit()
    return EntityOut(id=entity.id, type=entity.type, data=entity.data)
