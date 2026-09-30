from fastapi import APIRouter
from pydantic import BaseModel

from src.services.code_qa import answer_code_question


router = APIRouter(prefix="/api/qa", tags=["qa"])


class QARequest(BaseModel):
    question: str
    path: str = "."
    max_results: int = 3


@router.post("")
def code_question(request: QARequest):
    return answer_code_question(
        request.path,
        request.question,
        max_results=request.max_results,
    )
