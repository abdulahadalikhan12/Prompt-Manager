from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from schemas import PromptCreate, PromptUpdate, PromptOut
from services.prompt_service import PromptService

router = APIRouter(prefix="/prompts", tags=["prompts"])


def get_prompt_service(db: Session = Depends(get_db)) -> PromptService:
    """
    FastAPI dependency that builds a PromptService, handing it the
    request-scoped db session. Routes ask for this instead of
    constructing PromptService(db) themselves -- same Depends pattern
    used for get_db itself, just one layer up.
    """
    return PromptService(db)


@router.post("", response_model=PromptOut, status_code=201)
def create_prompt(payload: PromptCreate, service: PromptService = Depends(get_prompt_service)):
    return service.create(payload)


@router.get("", response_model=list[PromptOut])
def list_prompts(
    limit: Optional[int] = Query(default=None),
    service: PromptService = Depends(get_prompt_service),
):
    return service.list(limit=limit)


@router.get("/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: UUID, service: PromptService = Depends(get_prompt_service)):
    prompt = service.get(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.put("/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: UUID, payload: PromptUpdate, service: PromptService = Depends(get_prompt_service)):
    prompt = service.update(prompt_id, payload)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.delete("/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: UUID, service: PromptService = Depends(get_prompt_service)):
    deleted = service.delete(prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return None


@router.get("/{prompt_id}/exists")
def check_prompt_exists(prompt_id: UUID, service: PromptService = Depends(get_prompt_service)):
    return {"exists": service.exists(prompt_id)}
