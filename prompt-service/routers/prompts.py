from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Prompt
from schemas import PromptCreate, PromptUpdate, PromptOut

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=PromptOut, status_code=201)
def create_prompt(payload: PromptCreate, db: Session = Depends(get_db)):
    # Build a new ORM object from the validated request body. At this
    # point it only exists in Python memory, not in Postgres yet.
    new_prompt = Prompt(**payload.model_dump())

    db.add(new_prompt)       # stage it for insertion
    db.commit()              # actually execute the INSERT and save it
    db.refresh(new_prompt)   # pull back server-generated fields (id, timestamps)

    return new_prompt


@router.get("", response_model=list[PromptOut])
def list_prompts(
    tag: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Prompt)

    if tag is not None:
        # tags is stored as a comma-separated string (per spec), so we
        # match any prompt whose tags column CONTAINS this tag as a
        # substring. Not a perfect match (e.g. "sales" would also match
        # "salesforce"), but matches the simple comma-separated design
        # the spec asked for rather than introducing a separate tags table.
        query = query.filter(Prompt.tags.contains(tag))

    if limit is not None:
        query = query.limit(limit)

    return query.all()


@router.get("/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: UUID, db: Session = Depends(get_db)):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.put("/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: UUID, payload: PromptUpdate, db: Session = Depends(get_db)):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # exclude_unset=True is the key to "partial update": it only includes
    # fields the client actually sent in the request body. A field left
    # out entirely is skipped here, NOT overwritten with None.
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(prompt, field, value)

    db.commit()
    db.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: UUID, db: Session = Depends(get_db)):
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    db.delete(prompt)
    db.commit()
    return None


@router.get("/{prompt_id}/exists")
def check_prompt_exists(prompt_id: UUID, db: Session = Depends(get_db)):
    # Lighter than get_prompt: we only need to know if a row exists,
    # not fetch its full content. Used by review-service to validate
    # a prompt_id without pulling the whole prompt over the wire.
    exists = db.query(Prompt.id).filter(Prompt.id == prompt_id).first() is not None
    return {"exists": exists}
