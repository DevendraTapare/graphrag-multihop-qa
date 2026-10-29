from fastapi import APIRouter, Request

from app.graph_rag.models import GraphRequest, GraphResponse

router = APIRouter(prefix="/api/v1/rag/graph")


@router.post("/query", response_model=GraphResponse)
def query(body: GraphRequest, request: Request):
    return request.app.state.graph_service.query(
        body.question, body.max_hops, request.state.request_id
    )
