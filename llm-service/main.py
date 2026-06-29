from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from routers import llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Creates ONE httpx.AsyncClient when the app starts, and closes it
    when the app shuts down. This is the brief's "one shared client per
    service" requirement: opening a new AsyncClient on every single
    request would mean re-establishing TCP/TLS connections constantly.
    A shared client reuses connections across requests via an internal
    connection pool.
    """
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="LLM Service",
    description="Stateless gateway to OpenRouter -- no database, no local storage.",
    lifespan=lifespan,
)

app.include_router(llm.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "llm-service"}
