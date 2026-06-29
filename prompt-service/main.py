from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

import models  # noqa: F401 -- kept so SQLAlchemy's metadata stays aware of Prompt, Chat, Message
from routers import prompts, chats

# NOTE: table creation is handled by Alembic migrations now, not by
# Base.metadata.create_all(). Run `alembic upgrade head` once before
# starting this service for the first time -- see README.


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Week 2 addition: a single shared httpx.AsyncClient for every
    outbound call to llm-service, created once at startup and reused
    across all requests -- same pattern as llm-service's own client,
    and for the same reason (avoid re-establishing connections per
    request).
    """
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="Prompt Service",
    description="Stores, retrieves, updates, and deletes prompts in Postgres. Orchestrates execution via llm-service.",
    lifespan=lifespan,
)

app.include_router(prompts.router)
app.include_router(chats.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "prompt-service"}
