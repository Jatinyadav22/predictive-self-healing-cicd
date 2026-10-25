from fastapi import APIRouter
from src.services.audit_service import audit_logger

router = APIRouter(prefix="/api/audit", tags=["Audit"])

@router.get("/events")
def list_events(limit: int = 50):
    return audit_logger.list_audit_events(limit=limit)

@router.get("/metrics")
def get_metrics():
    return audit_logger.get_platform_metrics()
