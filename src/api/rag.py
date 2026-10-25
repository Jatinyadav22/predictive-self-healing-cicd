from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.services.rag_service import generate_rag_answer, get_rag_index_status

router = APIRouter(
    prefix="/api/rag",
    tags=["rag"],
)

class RAGRequest(BaseModel):
    question: str
    max_results: int = Field(default=3, ge=1, le=10)

@router.post("/query")
@router.post("/ask")
def rag_query(request: RAGRequest):
    return generate_rag_answer(
        request.question,
        max_results=request.max_results,
    )

@router.get("/status")
def rag_status():
    return get_rag_index_status()
