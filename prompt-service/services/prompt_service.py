from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models import Prompt
from schemas import PromptCreate, PromptUpdate


class PromptService:
    """
    All business logic for prompts lives here, not in the router.

    The router's only job is to translate HTTP concepts (path params,
    request bodies, status codes) into calls on this class, and translate
    this class's plain Python answers (a Prompt object, or None) back
    into HTTP responses. This mirrors the separation we used in the
    earlier notes-app project, and the reason is the same: if the
    storage mechanism ever changed, only this file would need to change,
    not the route definitions or their URL contracts.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: PromptCreate) -> Prompt:
        new_prompt = Prompt(**payload.model_dump())
        self.db.add(new_prompt)
        self.db.commit()
        self.db.refresh(new_prompt)
        return new_prompt

    def list(self, limit: Optional[int] = None) -> list[Prompt]:
        query = self.db.query(Prompt)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def get(self, prompt_id: UUID) -> Optional[Prompt]:
        return self.db.query(Prompt).filter(Prompt.id == prompt_id).first()

    def update(self, prompt_id: UUID, payload: PromptUpdate) -> Optional[Prompt]:
        prompt = self.get(prompt_id)
        if prompt is None:
            return None

        # exclude_unset=True is what makes partial update work -- only
        # fields actually present in the request body get applied.
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(prompt, field, value)

        self.db.commit()
        self.db.refresh(prompt)
        return prompt

    def delete(self, prompt_id: UUID) -> bool:
        prompt = self.get(prompt_id)
        if prompt is None:
            return False
        self.db.delete(prompt)
        self.db.commit()
        return True

    def exists(self, prompt_id: UUID) -> bool:
        return self.db.query(Prompt.id).filter(Prompt.id == prompt_id).first() is not None
