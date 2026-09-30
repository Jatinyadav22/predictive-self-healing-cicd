from fastapi import FastAPI

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
