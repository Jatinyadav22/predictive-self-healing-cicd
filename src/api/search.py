from fastapi import APIRouter
from pydantic import BaseModel

from src.services.semantic_code_search import semantic_search
from src.services.sourcegraph_search import sourcegraph_search


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


@router.post("/sourcegraph")
def sourcegraph_code_search(request: SearchRequest):
    results = sourcegraph_search(
        request.query,
        max_results=request.max_results,
    )

    return {
        "query": request.query,
        "results": results,
    }


class SourcegraphExplainRequest(BaseModel):
    repository: str
    path: str
    line_number: int
    preview: str


@router.post("/sourcegraph/explain")
def explain_sourcegraph_result(request: SourcegraphExplainRequest):
    from src.services.sourcegraph_explain import explain_sourcegraph_result as generate_sourcegraph_explanation

    explanation = generate_sourcegraph_explanation(
        repository=request.repository,
        path=request.path,
        line_number=request.line_number,
        preview=request.preview,
    )

    return {
        "repository": request.repository,
        "path": request.path,
        "line_number": request.line_number,
        "explanation": explanation,
    }
