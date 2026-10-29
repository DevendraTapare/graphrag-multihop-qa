import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.graph.schema import DIRECTIONS, FactType, Label


class GraphFailure(RuntimeError):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


class Budget:
    def __init__(self, seconds):
        self.deadline = time.perf_counter() + seconds

    def remaining(self):
        value = self.deadline - time.perf_counter()
        if value <= 0:
            raise GraphFailure("graph_request_timeout")
        return value


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class GraphRequest(Contract):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    question: str = Field(min_length=1, max_length=1000)
    max_hops: int = Field(default=3, ge=1, le=3)

    @field_validator("question")
    @classmethod
    def readable(cls, value):
        if not value.strip() or any(ord(c) < 32 and c not in "\r\n\t" for c in value):
            raise ValueError("Readable nonblank question required")
        return value.strip()


class Step(Contract):
    relation: FactType
    direction: Literal["outgoing", "incoming"] = "outgoing"

    @property
    def types(self):
        source, target = DIRECTIONS[self.relation]
        return (source, target) if self.direction == "outgoing" else (target, source)


class Context(Contract):
    entity_type: Label
    mention: str = Field(min_length=1, max_length=200)


class Plan(Contract):
    mention: str = Field(min_length=1, max_length=200)
    start_type: Label
    steps: tuple[Step, ...] = Field(min_length=1, max_length=3)
    answer_type: Label
    contexts: tuple[Context, ...] = ()
    multiple: bool = False
    rule_id: str
    parsing_status: Literal["supported"] = "supported"

    @property
    def hop_count(self):
        return len(self.steps)

    @property
    def node_types(self):
        return (self.start_type, *[s.types[1] for s in self.steps])

    @model_validator(mode="after")
    def coherent(self):
        label = self.start_type
        for step in self.steps:
            if step.types[0] != label:
                raise ValueError("Invalid relationship direction/type sequence")
            label = step.types[1]
        if label != self.answer_type:
            raise ValueError("Invalid answer type")
        return self


class Resolution(Contract):
    status: Literal["resolved", "ambiguous", "not_found"]
    canonical_id: str | None = None
    candidate_ids: tuple[str, ...] = ()
    reason: str


class EntityView(Contract):
    id: str
    name: str
    entity_type: Label
    scope: str


class Citation(Contract):
    fact_id: str
    document_id: str
    chunk_id: str
    quote: str
    start: int
    end: int
    source_kind: Literal["curated", "automatic"]
    source_id: str | None = None
    content_hash: str
    processing_version: str | None = None
    extraction_method: str


class EvidenceChunk(Contract):
    document_id: str
    chunk_id: str
    start: int
    end: int
    text: str
    content_hash: str
    source_kind: Literal["curated", "automatic"]


class ReasoningStep(Contract):
    source: EntityView
    relation: FactType
    target: EntityView
    direction: Literal["outgoing", "incoming"]
    stored_source_id: str
    stored_target_id: str
    supports: tuple[Citation, ...]


class EvidencePath(Contract):
    nodes: tuple[EntityView, ...]
    steps: tuple[ReasoningStep, ...]
    hop_count: int


class GraphResponse(Contract):
    answer: str | None
    answers: tuple[EntityView, ...] = ()
    abstained: bool
    reason: str
    retrieval_mode: Literal["graph_multi_hop"] = "graph_multi_hop"
    generator: Literal["deterministic_graph_v1"] = "deterministic_graph_v1"
    request_id: str
    plan: Plan | None
    resolution: Resolution | None
    hop_count: int
    reasoning_path: tuple[ReasoningStep, ...] = ()
    reasoning_paths: tuple[EvidencePath, ...] = ()
    citations: tuple[Citation, ...] = ()
    evidence_chunks: tuple[EvidenceChunk, ...] = ()
    candidate_path_count: int = 0
    paths_discarded: int = 0
    diagnostics: dict[str, int] = Field(default_factory=dict)
    latency_ms: dict[str, float]
