import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from core.config import settings
from schemas import GenerateRequest, GenerateResponse, SummarizeRequest, SummarizeResponse
from services.openrouter_client import OpenRouterClient
from services.summarize_service import summarize_chat

router = APIRouter()


def get_client(request: Request) -> OpenRouterClient:
    """
    Pulls the single shared httpx.AsyncClient off app.state (created
    once at startup, see main.py's lifespan) and wraps it in an
    OpenRouterClient.
    """
    return OpenRouterClient(request.app.state.http_client)


@router.post("/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest, request: Request):
    client = get_client(request)
    return await client.generate(
        messages=payload.messages,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )


@router.post("/generate/stream")
async def generate_stream(payload: GenerateRequest, request: Request):
    """
    Separate endpoint from /generate rather than a flag-driven branch
    inside it, because the RESPONSE TYPE is fundamentally different.
    """
    client = get_client(request)

    async def event_generator():
        async for chunk in client.stream_generate(
            messages=payload.messages, model=payload.model, temperature=payload.temperature,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(payload: SummarizeRequest, request: Request):
    client = get_client(request)
    return await summarize_chat(client, payload.messages)


@router.get("/models")
async def list_models(request: Request):
    http_client: httpx.AsyncClient = request.app.state.http_client
    response = await http_client.get(
        f"{settings.OPENROUTER_BASE_URL}/models",
        headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
    )
    return response.json()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "llm-service",
        "api_key_configured": bool(settings.OPENROUTER_API_KEY),
        "model_chain": settings.MODEL_CHAIN,
    }
