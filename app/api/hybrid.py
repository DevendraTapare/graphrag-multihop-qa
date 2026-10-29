from fastapi import APIRouter, Request

from app.aligned.models import AlignedGraphResponse, HybridRequest, HybridResponse
from app.graph_rag.models import GraphRequest
from app.vector.models import QueryRequest

router = APIRouter(prefix="/api/v1/rag")


@router.post("/hybrid/query", response_model=HybridResponse)
def hybrid(body: HybridRequest, request: Request):
    return request.app.state.aligned.hybrid.query(
        body.question, body.top_k, body.max_hops, request.state.request_id
    )


@router.post("/aligned/graph/query", response_model=AlignedGraphResponse)
def graph(body: GraphRequest, request: Request):
    return request.app.state.aligned.graph.query(
        body.question, body.max_hops, request.state.request_id
    )


@router.post("/aligned/vector/query")
def vector(body: QueryRequest, request: Request):
    response = request.app.state.aligned.vector.retrieve_vector_only(body.question, body.top_k)
    return {**response.model_dump(mode="json"), "request_id": request.state.request_id}


@router.get("/aligned/ready")
def ready(request: Request):
    from fastapi.responses import JSONResponse

    available = request.app.state.aligned.db.ready()
    return JSONResponse(
        {"status": "ready" if available else "unavailable"}, 200 if available else 503
    )
