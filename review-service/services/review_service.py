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
    translates HTTP in and out. review-service still has NO database
    connection anywhere in this file or anywhere else in the service --
    this class is the proof: it only ever does HTTP calls and file I/O,
    never SQL.

    Week 2 adds chat reviews alongside Week 1's prompt reviews. Both
    paths share the same underlying logic (fetch a snapshot from
    prompt-service, distinguish 404 vs 503, save to a JSON file) --
    only WHICH endpoint on prompt-service gets called, and what counts
    as the "content" to snapshot, differs.
    """

    def __init__(self, storage: ReviewStorage, http_client: httpx.AsyncClient):
        self.storage = storage
        self.http_client = http_client  # shared client, created once in main.py's lifespan -- not per-call

    async def create(self, payload: ReviewCreate) -> dict:
        if payload.target_type == "chat":
            snapshot = await self._fetch_chat_snapshot(payload.chat_id)
        else:
            snapshot = await self._fetch_prompt_snapshot(payload.prompt_id)

        return self.storage.create(
            target_type=payload.target_type,
            prompt_id=str(payload.prompt_id) if payload.prompt_id else None,
            chat_id=str(payload.chat_id) if payload.chat_id else None,
            snapshot=snapshot,
            reviewer_name=payload.reviewer_name,
            score=payload.score,
            feedback=payload.feedback,
        )

    async def _fetch_prompt_snapshot(self, prompt_id: UUID) -> str:
        """Week 1 behavior, unchanged: GET /prompts/{id} on prompt-service,
        snapshot is just the prompt's text content."""
        response = await self._get(f"/prompts/{prompt_id}")
        return response["content"]

    async def _fetch_chat_snapshot(self, chat_id: UUID) -> dict:
        """
        Week 2 addition: GET /chats/{chat_id} on prompt-service, which
        returns the full conversation (all messages, in order, plus the
        running token total). The ENTIRE chat object is stored verbatim
        as the snapshot -- not just the latest message -- so a reviewer
        can later see exactly what was reviewed even if the live chat
        gains more messages afterward.
        """
        return await self._get(f"/chats/{chat_id}")

    async def _get(self, path: str) -> dict:
        """
        Shared GET-and-error-handle logic for both snapshot fetches.
        Same 404-vs-503 distinction as Week 1, now reused for two
        different prompt-service endpoints instead of duplicated.
        """
        try:
            response = await self.http_client.get(
                f"{settings.PROMPT_SERVICE_URL}{path}",
                timeout=5.0,
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="prompt-service is unavailable. Could not verify the target.",
            )

        if response.status_code == 404:
            target = "Chat" if "/chats/" in path else "Prompt"
            raise HTTPException(status_code=404, detail=f"{target} not found")

        if response.status_code != 200:
            raise HTTPException(
                status_code=503,
                detail="prompt-service returned an unexpected error.",
            )

        return response.json()

    def list_reviews(self, prompt_id: Optional[UUID] = None, chat_id: Optional[UUID] = None) -> list[dict]:
        return self.storage.get_all(
            prompt_id=str(prompt_id) if prompt_id else None,
            chat_id=str(chat_id) if chat_id else None,
        )

    def get(self, review_id: UUID) -> Optional[dict]:
        return self.storage.get(str(review_id))

    def summary_for_prompt(self, prompt_id: UUID) -> ReviewSummary:
        return self._build_summary(prompt_id, self.storage.get_all(prompt_id=str(prompt_id)))

    def summary_for_chat(self, chat_id: UUID) -> ReviewSummary:
        return self._build_summary(chat_id, self.storage.get_all(chat_id=str(chat_id)))

    def _build_summary(self, target_id: UUID, reviews: list[dict]) -> ReviewSummary:
        if not reviews:
            return ReviewSummary(target_id=target_id, average_score=None, review_count=0, feedback=[])

        scores = [r["score"] for r in reviews]
        feedback = [r["feedback"] for r in reviews]

        return ReviewSummary(
            target_id=target_id,
            average_score=sum(scores) / len(scores),
            review_count=len(reviews),
            feedback=feedback,
        )
