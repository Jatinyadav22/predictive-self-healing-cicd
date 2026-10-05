from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.services.test_generation_service import generate_tests


router = APIRouter(
    prefix="/api/test-generation",
    tags=["test-generation"],
)


class TestGenerationRequest(BaseModel):
    request: str
    max_results: int = Field(default=5, ge=1, le=10)


@router.post("/generate")
def test_generation(request: TestGenerationRequest):
    return generate_tests(
        request.request,
        max_results=request.max_results,
    )
