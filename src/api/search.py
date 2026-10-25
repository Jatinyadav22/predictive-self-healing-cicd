from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from src.services.semantic_code_search import semantic_search
from src.services.sourcegraph_search import sourcegraph_search

router = APIRouter(prefix="/api/search", tags=["search"])

class SearchRequest(BaseModel):
    query: str
    path: str = "."
    max_results: int = 5

@router.get("/semantic")
def semantic_code_search_get(query: str = "", path: str = ".", max_results: int = 5):
    return _do_semantic_search(query, path, max_results)

@router.post("/semantic")
def semantic_code_search_post(request: SearchRequest):
    return _do_semantic_search(request.query, request.path, request.max_results)

def _do_semantic_search(query: str, path: str, max_results: int):
    if not query.strip():
        return {"query": "", "results": []}

    try:
        from src.services.rag_service import retrieve_repository_context
        chroma_res = retrieve_repository_context(query, max_results=max_results)
        if chroma_res:
            results = [
                {
                    "path": r.get("source", "repository"),
                    "similarity": round(float(r.get("score", 0.95)), 3),
                    "content": r.get("content", "")[:600]
                }
                for r in chroma_res
            ]
            return {"query": query, "results": results}
    except Exception:
        pass

    results = semantic_search(path, query, max_results=max_results)
    return {"query": query, "results": results}

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
