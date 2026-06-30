from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from routers import reviews


@asynccontextmanager
async def lifespan(app: FastAPI):
    """One shared httpx.AsyncClient for the service's lifetime, same
    pattern as prompt-service and llm-service -- created once, reused
    for every outbound call to prompt-service, closed on shutdown."""
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="Review Service",
    description="Reviews prompts and chats by fetching snapshots from prompt-service via HTTP. Stores reviews as JSON files.",
    lifespan=lifespan,
)

app.include_router(reviews.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "review-service"}
