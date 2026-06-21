from fastapi import FastAPI

import models  # noqa: F401 -- kept so SQLAlchemy's metadata stays aware of Prompt
from routers import prompts

# NOTE: table creation is handled by Alembic migrations now, not by
# Base.metadata.create_all(). Run `alembic upgrade head` once before
# starting this service for the first time -- see README.

app = FastAPI(
    title="Prompt Service",
    description="Stores, retrieves, updates, and deletes prompts in Postgres.",
)

app.include_router(prompts.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "prompt-service"}
