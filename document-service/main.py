from fastapi import FastAPI

from routers import documents

app = FastAPI(
    title="Document Service",
    description="Accepts PDF/DOCX uploads, stores them on local disk, returns extracted text.",
)

app.include_router(documents.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "document-service"}
