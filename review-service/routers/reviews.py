from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from schemas import ReviewCreate, ReviewOut, ReviewSummary
from storage import ReviewStorage
from services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


def get_review_service() -> ReviewService:
    """
    Same Depends pattern as prompt-service's get_prompt_service --
    builds the storage layer and hands a ReviewService to the route.
    """
    storage = ReviewStorage(directory="reviews")
    return ReviewService(storage)


@router.post("", response_model=ReviewOut, status_code=201)
async def create_review(payload: ReviewCreate, service: ReviewService = Depends(get_review_service)):
    return await service.create(payload)


@router.get("", response_model=list[ReviewOut])
def list_reviews(prompt_id: Optional[UUID] = Query(default=None), service: ReviewService = Depends(get_review_service)):
    return service.list(prompt_id=prompt_id)


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: UUID, service: ReviewService = Depends(get_review_service)):
    review = service.get(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.get("/{prompt_id}/summary", response_model=ReviewSummary)
def get_review_summary(prompt_id: UUID, service: ReviewService = Depends(get_review_service)):
    return service.summary(prompt_id)
