from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.repository_scanner import scan_repository


router = APIRouter(prefix="/api/repository", tags=["Repository"])


class RepositoryIndexRequest(BaseModel):
    path: str = "."


@router.post("/index")
def index_repository(request: RepositoryIndexRequest):
    try:
        return scan_repository(request.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
