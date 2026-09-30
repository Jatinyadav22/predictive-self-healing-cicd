from fastapi import APIRouter
from pydantic import BaseModel

from src.services.semantic_code_search import semantic_search


router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    path: str = "."
    max_results: int = 5


@router.post("/semantic")
def semantic_code_search(request: SearchRequest):
    results = semantic_search(
        request.path,
        request.query,
        max_results=request.max_results,
    )

    return {
        "query": request.query,
        "results": results,
    }
