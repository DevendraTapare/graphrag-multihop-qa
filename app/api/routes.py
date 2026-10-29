from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
def ready(request: Request) -> JSONResponse:
    if request.app.state.database.ready():
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "unavailable", "request_id": request.state.request_id}, 503)
