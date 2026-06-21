from collections import defaultdict
from uuid import UUID
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

from config import PROMPT_SERVICE_URL
from schemas import ReviewCreate, ReviewOut, ReviewSummary
from storage import ReviewStorage

router = APIRouter(prefix="/reviews", tags=["reviews"])

storage = ReviewStorage(directory="reviews")


@router.post("", response_model=ReviewOut, status_code=201)
async def create_review(payload: ReviewCreate):
    # Step 1: ask prompt-service whether this prompt actually exists,
    # and get its content, by calling its HTTP API -- NOT its database.
    # review-service has no idea Postgres is even involved on the other
    # side; all it knows is "GET this URL, get back JSON."
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PROMPT_SERVICE_URL}/prompts/{payload.prompt_id}",
                timeout=5.0,
            )
    except httpx.RequestError:
        # prompt-service is down, unreachable, or timed out entirely --
        # this is a NETWORK-level failure, distinct from a 404.
        raise HTTPException(
            status_code=503,
            detail="prompt-service is unavailable. Could not verify the prompt.",
        )

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if response.status_code != 200:
        # Catch-all for any other unexpected response from prompt-service
        # (e.g. a 500 on their end) -- we still don't want to crash.
        raise HTTPException(
            status_code=503,
            detail="prompt-service returned an unexpected error.",
        )

    prompt_data = response.json()

    # Step 2: build the review, copying the prompt's content verbatim
    # into prompt_snapshot. This snapshot will NOT change even if the
    # original prompt is edited later -- it's a copy, not a live reference.
    review = storage.create(
        prompt_id=str(payload.prompt_id),
        prompt_snapshot=prompt_data["content"],
        reviewer_name=payload.reviewer_name,
        score=payload.score,
        feedback=payload.feedback,
    )
    return review


@router.get("", response_model=list[ReviewOut])
def list_reviews(prompt_id: Optional[UUID] = Query(default=None)):
    filter_id = str(prompt_id) if prompt_id else None
    return storage.get_all(prompt_id=filter_id)


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: UUID):
    review = storage.get(str(review_id))
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.get("/{prompt_id}/summary", response_model=ReviewSummary)
def get_review_summary(prompt_id: UUID):
    reviews = storage.get_all(prompt_id=str(prompt_id))

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
