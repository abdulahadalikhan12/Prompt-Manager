from fastapi import FastAPI

from routers import reviews

app = FastAPI(
    title="Review Service",
    description="Fetches prompts from prompt-service via HTTP and stores reviews as JSON files.",
)

app.include_router(reviews.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "review-service"}
