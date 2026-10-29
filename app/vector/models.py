from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VectorFailure(RuntimeError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("question")
    @classmethod
    def meaningful(cls, value):
        if not value.strip() or any(ord(c) < 32 and c not in "\t\r\n" for c in value):
            raise ValueError("Question must contain readable text")
        return value.strip()


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_id: str
    chunk_id: str
    source_id: str
    source_filename: str
    original_document_id: str | None
    content_hash: str
    chunk_hash: str
    processing_version: str
    ingestion_id: str
    embedding_version: str
    start: int
    end: int
    text: str
    # Complete, non-code source sentence bounds, relative to this exact chunk.
    sentence_starts: list[int] = Field(default_factory=list)
    sentence_ends: list[int] = Field(default_factory=list)
    score: float = Field(ge=0, le=1)


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    quote: str
    start: int
    end: int


class QueryResponse(BaseModel):
    answer: str | None
    abstained: bool
    reason: str
    retrieved_chunks: list[RetrievedChunk]
    citations: list[Citation]
    retrieval_mode: Literal["vector_only"] = "vector_only"
    generator: Literal["deterministic_text_v1"] = "deterministic_text_v1"
    embedding_model: str
    embedding_version: str
    corpus_build: str
    latency_ms: dict[str, float]
