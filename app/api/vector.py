from fastapi import APIRouter, Request

from app.vector.models import QueryRequest, QueryResponse

router = APIRouter(prefix="/api/v1/rag/vector")


@router.post("/query", response_model=QueryResponse)
def query(body: QueryRequest, request: Request):
    return request.app.state.vector_service.retrieve_vector_only(body.question, body.top_k)
