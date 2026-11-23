from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from src.api.repository import router as repository_router
from src.api.search import router as search_router
from src.api.qa import router as qa_router
from src.api.rag import router as rag_router
from src.api.test_generation import router as test_generation_router
from src.api.pipeline import router as pipeline_router
from src.api.risk import router as risk_router
from src.api.audit import router as audit_router

app = FastAPI(
    title="Predictive & Explainable Self-Healing CI/CD",
    version="0.2.0",
    description="Autonomous AI DevOps platform with failure prediction, RAG root-cause analysis, and self-healing.",
)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "predictive-self-healing-cicd",
        "version": "0.2.0"
    }

# Include existing Milestone 1 & 2 routers
app.include_router(repository_router)
app.include_router(search_router)
app.include_router(qa_router)
app.include_router(rag_router)
app.include_router(test_generation_router)

# Include Predictive & Self-Healing Platform routers
app.include_router(pipeline_router)
app.include_router(risk_router)
app.include_router(audit_router)

# Direct Webhook alias for /api/webhooks/github
from fastapi import Request
from src.api.pipeline import github_webhook_endpoint
@app.post("/api/webhooks/github")
async def root_github_webhook(request: Request):
    return await github_webhook_endpoint(request)

# Mount static web assets
static_dir = Path("src/static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
def dashboard():
    return FileResponse("src/static/index.html")

@app.post("/api/simulate-push")
def simulate_push_direct_alias():
    from src.api.pipeline import heal_and_push_endpoint
    return heal_and_push_endpoint()
