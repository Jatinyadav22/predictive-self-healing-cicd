from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.services.test_generation_service import (
    generate_tests,
    validate_generated_test,
    execute_test_isolated
)

router = APIRouter(
    prefix="/api/test-generation",
    tags=["test-generation"],
)

class TestGenerationRequest(BaseModel):
    request: str
    max_results: int = Field(default=5, ge=1, le=10)

class TestValidationRequest(BaseModel):
    test_code: str

class TestExecutionRequest(BaseModel):
    test_code: str
    target_dir: str = "demo_repo"
    timeout: int = Field(default=15, ge=1, le=60)

@router.post("/generate")
def test_generation(request: TestGenerationRequest):
    return generate_tests(
        request.request,
        max_results=request.max_results,
    )

@router.post("/validate")
def test_validation(request: TestValidationRequest):
    return validate_generated_test(request.test_code)

@router.post("/execute")
def test_execution(request: TestExecutionRequest):
    return execute_test_isolated(
        request.test_code,
        target_dir=request.target_dir,
        timeout=request.timeout
    )

