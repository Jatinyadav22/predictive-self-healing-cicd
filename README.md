# Predictive & Explainable Self-Healing CI/CD

An AI-powered DevOps system that combines CI/CD automation, repository intelligence,
semantic code search, Retrieval-Augmented Generation (RAG), failure prediction,
root-cause analysis, explainability, automated test generation, and controlled
self-healing workflows.

## Current Status

Milestone M1 — Application Foundation

- Python 3.12
- FastAPI
- Uvicorn
- Pydantic
- Environment-based configuration
- Health-check API

## Run Locally

Activate the virtual environment:

```bash
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000

