from fastapi import FastAPI

from database import Base, engine
import models  # noqa: F401 -- must be imported so SQLAlchemy registers the Prompt model
from routers import prompts

# Creates the "prompts" table if it doesn't already exist. Equivalent
# to the spec's "Database and table are created on startup if they do
# not exist" -- this is SQLAlchemy's version of CREATE TABLE IF NOT EXISTS.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Prompt Service",
    description="Stores, retrieves, updates, and deletes prompts in Postgres.",
)

app.include_router(prompts.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "prompt-service"}
