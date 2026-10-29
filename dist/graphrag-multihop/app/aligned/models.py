from typing import Literal

from pydantic import Field

from app.graph_rag.models import Contract, GraphRequest
from app.graph_rag.models import GraphResponse as OriginalGraphResponse
from app.vector.models import RetrievedChunk


class AlignedGraphResponse(OriginalGraphResponse):
    retrieval_mode: Literal["graph_only"] = "graph_only"
    generator: Literal["deterministic_aligned_graph_v1"] = "deterministic_aligned_graph_v1"


class HybridRequest(GraphRequest):
    top_k: int = Field(default=5, ge=1, le=10)


class FusedEvidence(Contract):
    document_id: str
    chunk_id: str
    vector_rank: int | None
    graph_rank: int | None
    rrf_score: float
    sources: tuple[Literal["vector", "graph"], ...]


class HybridResponse(AlignedGraphResponse):
    retrieval_mode: Literal["hybrid_graph_vector"] = "hybrid_graph_vector"
    generator: Literal["deterministic_hybrid_v1"] = "deterministic_hybrid_v1"
    vector_evidence: tuple[RetrievedChunk, ...] = ()
    candidate_entities: tuple[dict, ...] = ()
    fused_evidence: tuple[FusedEvidence, ...] = ()
    vector_answer_candidate: str | None = None
    entity_expansion: bool = True
    evidence_reranking: bool = True
