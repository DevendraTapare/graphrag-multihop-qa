import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.graph.schema import FactType, Label
from app.models.fixtures import Identifier


def utcnow() -> datetime:
    return datetime.now(UTC)


def stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(payload).hexdigest()[:40]}"


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class SourceDocument(Contract):
    id: Identifier
    source_id: Identifier
    source_filename: str = Field(min_length=1, max_length=300)
    text: str
    content_hash: Hash
    ingestion_version: Literal["local-utf8-v1"] = "local-utf8-v1"
    original_document_id: Identifier | None = None
    created_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def integrity(self):
        if self.content_hash != text_hash(self.text):
            raise ValueError("Document hash does not match original text")
        if self.id != stable_id("autodoc", self.source_id, self.content_hash):
            raise ValueError("Invalid document snapshot identity")
        if self.created_at.tzinfo is None:
            raise ValueError("Document timestamp requires timezone")
        return self


class ChunkOptions(Contract):
    size: int = Field(default=600, ge=32, le=16000)
    overlap: int = Field(default=80, ge=0)

    @model_validator(mode="after")
    def overlap_smaller_than_size(self):
        if self.overlap >= self.size:
            raise ValueError("Overlap must be smaller than chunk size")
        return self


class TextChunk(Contract):
    id: Identifier
    document_id: Identifier
    content_hash: Hash
    processing_version: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str


class EntityCandidate(Contract):
    id: Identifier
    mention: str = Field(min_length=1)
    label: Label
    source_document_id: Identifier
    source_chunk_id: Identifier
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    extraction_method: Literal["deterministic_rules"] = "deterministic_rules"
    extraction_version: str
    rule_score: float = Field(default=1, ge=0, le=1)


class RelationCandidate(Contract):
    id: Identifier
    subject: EntityCandidate
    object: EntityCandidate
    predicate: FactType
    source_document_id: Identifier
    source_chunk_id: Identifier
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    evidence: str = Field(min_length=1)
    rule_id: str
    extraction_method: Literal["deterministic_rules"] = "deterministic_rules"
    extraction_version: str
    rule_score: float = Field(default=1, ge=0, le=1)


class Rejection(Contract):
    candidate_id: str
    kind: Literal["entity", "relationship", "sentence"]
    reason: str
    source_document_id: str
    source_chunk_id: str | None = None
    start: int
    end: int
    text: str


class CandidateBatch(Contract):
    entities: list[EntityCandidate]
    relations: list[RelationCandidate]
    rejections: list[Rejection] = Field(default_factory=list)


class ResolvedEntity(Contract):
    candidate: EntityCandidate
    canonical_id: Identifier


class AcceptedFact(Contract):
    id: Identifier
    source_id: Identifier
    content_hash: Hash
    processing_version: str
    ingestion_version: str
    subject_id: Identifier
    object_id: Identifier
    candidate: RelationCandidate
    provenance_status: Literal["verified_rule"] = "verified_rule"
    created_at: datetime = Field(default_factory=utcnow)


class ValidatedExtraction(Contract):
    entities: list[ResolvedEntity]
    facts: list[AcceptedFact]
    rejections: list[Rejection]


class IngestionFailure(RuntimeError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)
