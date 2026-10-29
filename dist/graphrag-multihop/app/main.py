import logging
import re
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.aligned.components import AlignedComponents
from app.api.graph_rag import router as graph_router
from app.api.hybrid import router as hybrid_router
from app.api.routes import router
from app.api.vector import router as vector_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, request_id
from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient
from app.graph_rag.models import GraphFailure
from app.graph_rag.service import build_graph_service
from app.vector.embedding import MiniLM
from app.vector.models import VectorFailure
from app.vector.repository import VectorRepository
from app.vector.retrieval import VectorOnlyService

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    database=None,
    vector_service=None,
    graph_service=None,
    aligned=None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.neo4j_password.get_secret_value())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.database = database or GraphDatabaseClient(settings)
        embedder = MiniLM(settings.embedding_startup_timeout, settings.embedding_inference_timeout)
        app.state.vector_service = vector_service or VectorOnlyService(
            VectorRepository(app.state.database, settings.vector_corpus), embedder
        )
        app.state.graph_service = graph_service or build_graph_service(app.state.database, settings)
        app.state.aligned = aligned or AlignedComponents(settings)
        try:
            yield
        finally:
            embedder.close()
            app.state.aligned.close()
            app.state.database.close()

    app = FastAPI(title="GraphRAG for Multi-Hop Question Answering", lifespan=lifespan)

    @app.middleware("http")
    async def identify_request(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        rid = incoming if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", incoming) else uuid4().hex
        request.state.request_id = rid
        token = request_id.set(rid)
        try:
            try:
                response = await call_next(request)
            except Exception:
                logger.error("Unhandled request failure")
                response = JSONResponse({"error": "Internal server error", "request_id": rid}, 500)
            response.headers["X-Request-ID"] = rid
            logger.info(
                "Request completed status=%s method=%s", response.status_code, request.method
            )
            return response
        finally:
            request_id.reset(token)

    @app.exception_handler(DatabaseUnavailable)
    async def database_error(request: Request, exc: DatabaseUnavailable):
        return JSONResponse(
            {"error": "Graph database unavailable", "request_id": request.state.request_id}, 503
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            {"error": "Invalid request", "request_id": request.state.request_id}, 422
        )

    @app.exception_handler(VectorFailure)
    async def vector_error(request: Request, exc: VectorFailure):
        status = 422 if exc.category == "question_token_limit" else 503
        return JSONResponse({"error": exc.category, "request_id": request.state.request_id}, status)

    app.include_router(router)
    app.include_router(router, prefix="/api/v1")
    app.include_router(vector_router)
    app.include_router(graph_router)
    app.include_router(hybrid_router)

    @app.exception_handler(GraphFailure)
    async def graph_error(request: Request, exc: GraphFailure):
        status = 504 if exc.category in {"graph_request_timeout", "graph_query_timeout"} else 503
        return JSONResponse({"error": exc.category, "request_id": request.state.request_id}, status)

    return app
