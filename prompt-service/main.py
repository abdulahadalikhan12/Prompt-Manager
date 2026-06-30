from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

import models  # noqa: F401 -- kept so SQLAlchemy's metadata stays aware of Prompt, Chat, Message
from core.config import settings
from routers import prompts, chats
from run_migrations import run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup sequence, in order:

    1. (Optional, env-controlled) Apply any pending Alembic migrations
       automatically -- see run_migrations.py for why this exists and
       what it does and doesn't replace. Controlled by AUTO_MIGRATE in
       .env so local development can keep running `alembic upgrade head`
       manually if preferred, while a real deployment can set
       AUTO_MIGRATE=true and never need an interactive terminal at all.
    2. Create the single shared httpx.AsyncClient used for every
       outbound call to llm-service (Week 2 addition) -- created once,
       reused across all requests, closed on shutdown.
    """
    if settings.AUTO_MIGRATE:
        run_migrations()

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
