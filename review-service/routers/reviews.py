from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from schemas import ReviewCreate, ReviewOut, ReviewSummary
from storage import ReviewStorage
from services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


def get_review_service(request: Request) -> ReviewService:
    """Builds a ReviewService using the storage layer and the shared
    httpx.AsyncClient set up in main.py's lifespan."""
    storage = ReviewStorage(directory="reviews")
    return ReviewService(storage, request.app.state.http_client)


@router.post("", response_model=ReviewOut, status_code=201)
async def create_review(payload: ReviewCreate, service: ReviewService = Depends(get_review_service)):
    return await service.create(payload)


@router.get("", response_model=list[ReviewOut])
def list_reviews(
    prompt_id: Optional[UUID] = Query(default=None),
    chat_id: Optional[UUID] = Query(default=None),
    message_id: Optional[UUID] = Query(default=None),
    service: ReviewService = Depends(get_review_service),
):
    return service.list_reviews(prompt_id=prompt_id, chat_id=chat_id, message_id=message_id)


# More-specific paths declared BEFORE /{prompt_id}/summary so they win
# the routing match. Otherwise /chat/{id}/summary would be swallowed as
# a prompt UUID and fail validation.
@router.get("/chat/{chat_id}/summary", response_model=ReviewSummary)
def get_chat_review_summary(chat_id: UUID, service: ReviewService = Depends(get_review_service)):
    return service.summary_for_chat(chat_id)


@router.get("/message/{message_id}/summary", response_model=ReviewSummary)
def get_message_review_summary(message_id: UUID, service: ReviewService = Depends(get_review_service)):
    return service.summary_for_message(message_id)


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: UUID, service: ReviewService = Depends(get_review_service)):
    review = service.get(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.get("/{prompt_id}/summary", response_model=ReviewSummary)
def get_prompt_review_summary(prompt_id: UUID, service: ReviewService = Depends(get_review_service)):
    return service.summary_for_prompt(prompt_id)
