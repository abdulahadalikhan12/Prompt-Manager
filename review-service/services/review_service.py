from typing import Optional
from uuid import UUID

import httpx
from fastapi import HTTPException

from core.config import settings
from schemas import ReviewCreate, ReviewSummary
from storage import ReviewStorage


class ReviewService:
    """
    All business logic for reviews lives here -- the router only
    translates HTTP in and out. Specifically:
      - calling prompt-service over HTTP (httpx)
      - distinguishing "prompt not found" (404) from "prompt-service
        unreachable" (503)
      - delegating actual file reads/writes to ReviewStorage

    review-service still has NO database connection anywhere in this
    file or anywhere else in the service -- this class is the proof:
    it only ever does HTTP calls and file I/O, never SQL.
    """

    def __init__(self, storage: ReviewStorage):
        self.storage = storage

    async def create(self, payload: ReviewCreate) -> dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.PROMPT_SERVICE_URL}/prompts/{payload.prompt_id}",
                    timeout=5.0,
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="prompt-service is unavailable. Could not verify the prompt.",
            )

        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Prompt not found")

        if response.status_code != 200:
            raise HTTPException(
                status_code=503,
                detail="prompt-service returned an unexpected error.",
            )

        prompt_data = response.json()

        return self.storage.create(
            prompt_id=str(payload.prompt_id),
            prompt_snapshot=prompt_data["content"],
            reviewer_name=payload.reviewer_name,
            score=payload.score,
            feedback=payload.feedback,
        )

    def list(self, prompt_id: Optional[UUID] = None) -> list[dict]:
        filter_id = str(prompt_id) if prompt_id else None
        return self.storage.get_all(prompt_id=filter_id)

    def get(self, review_id: UUID) -> Optional[dict]:
        return self.storage.get(str(review_id))

    def summary(self, prompt_id: UUID) -> ReviewSummary:
        reviews = self.storage.get_all(prompt_id=str(prompt_id))

        if not reviews:
            return ReviewSummary(prompt_id=prompt_id, average_score=None, review_count=0, feedback=[])

        scores = [r["score"] for r in reviews]
        feedback = [r["feedback"] for r in reviews]

        return ReviewSummary(
            prompt_id=prompt_id,
            average_score=sum(scores) / len(scores),
            review_count=len(reviews),
            feedback=feedback,
        )
