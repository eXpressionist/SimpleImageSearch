from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check():
    # TODO: Add database connectivity check
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check():
    return {"status": "alive"}
