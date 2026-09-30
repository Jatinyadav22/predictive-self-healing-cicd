from fastapi import FastAPI

from src.api.repository import router as repository_router
from src.api.search import router as search_router
from src.api.qa import router as qa_router

app = FastAPI(
    title="Predictive & Explainable Self-Healing CI/CD",
    version="0.1.0",
    description="AI-powered DevOps pipeline intelligence and self-healing system.",
)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "predictive-self-healing-cicd",
    }


app.include_router(repository_router)
app.include_router(search_router)
app.include_router(qa_router)
