import hashlib
import json
import re
import unicodedata
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.graph.schema import DIRECTIONS, FactType, Label

Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9:_-]{1,95}$")]


def normalize_name(name: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Entity(StrictModel):
    id: Identifier
    label: Label
    name: str = Field(min_length=1, max_length=200)
    scope: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.name.strip() or not self.scope.strip():
            raise ValueError("Names and scopes must not be blank")
        return self


class Document(StrictModel):
    id: Identifier
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)


class Chunk(StrictModel):
    id: Identifier
    document_id: Identifier
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)


class Fact(StrictModel):
    id: Identifier
    subject: Identifier
    predicate: FactType
    object: Identifier
    source_document_id: Identifier
    source_chunk_id: Identifier
    quote: str = Field(min_length=1)
    extraction_method: Literal["manual_fixture"] = "manual_fixture"
    confidence: float = Field(ge=0, le=1, default=1)
    created_at: datetime


class Evaluation(StrictModel):
    id: Identifier
    question: str = Field(min_length=1)
    answerable: bool
    expected_answer: str | None
    expected_path: list[Identifier]
    source_document_ids: list[Identifier]
    supporting_fact_ids: list[Identifier]
    reason: str | None = None


class Fixture(StrictModel):
    id: Identifier
    entities: list[Entity]
    documents: list[Document]
    chunks: list[Chunk]
    facts: list[Fact]

    @model_validator(mode="after")
    def integrity(self):
        nodes = [*self.entities, *self.documents, *self.chunks]
        ids = [n.id for n in nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate node identifiers")
        entities = {e.id: e for e in self.entities}
        documents = {d.id: d for d in self.documents}
        chunks = {c.id: c for c in self.chunks}
        logical = [(e.label, normalize_name(e.name), e.scope) for e in self.entities]
        if len(logical) != len(set(logical)):
            raise ValueError("Duplicate logical entity within a scope")
        for c in self.chunks:
            if c.document_id not in documents:
                raise ValueError("Orphan chunk document")
            if documents[c.document_id].text[c.start : c.end] != c.text:
                raise ValueError("Chunk offsets do not match source text")
        fact_ids = [f.id for f in self.facts]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("Duplicate fact identifiers")
        signatures = set()
        for f in self.facts:
            if f.subject not in entities or f.object not in entities:
                raise ValueError("Missing fact endpoint")
            if (entities[f.subject].label, entities[f.object].label) != DIRECTIONS[f.predicate]:
                raise ValueError("Incorrect fact direction or endpoint labels")
            c = chunks.get(f.source_chunk_id)
            if c is None or c.document_id != f.source_document_id or f.quote not in c.text:
                raise ValueError("Missing or inconsistent fact evidence")
            if f.created_at.tzinfo is None:
                raise ValueError("Fact timestamp must have a timezone")
            signature = (f.subject, f.predicate, f.object, f.source_chunk_id)
            if signature in signatures:
                raise ValueError("Duplicate logical fact")
            signatures.add(signature)
        return self


def fingerprint(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def edge_id(kind: str, source: str, target: str) -> str:
    digest = hashlib.sha256(f"{kind}|{source}|{target}".encode()).hexdigest()[:24]
    return f"edge:{digest}"


def validate_evaluations(fixture: Fixture, evaluations: list[Evaluation]) -> None:
    if len({e.id for e in evaluations}) != len(evaluations):
        raise ValueError("Duplicate evaluation identifiers")
    facts = {f.id: f for f in fixture.facts}
    for e in evaluations:
        if not e.answerable:
            if e.expected_answer is not None or e.expected_path or e.supporting_fact_ids:
                raise ValueError("Unanswerable question claims an answer")
            if e.source_document_ids or not e.reason:
                raise ValueError("Unanswerable question needs a reason and no citations")
            continue
        if not e.expected_answer or not e.supporting_fact_ids:
            raise ValueError("Answerable question lacks evidence")
        if len(e.expected_path) != len(e.supporting_fact_ids) + 1:
            raise ValueError("Path length mismatch")
        selected = [facts[fid] for fid in e.supporting_fact_ids if fid in facts]
        if len(selected) != len(e.supporting_fact_ids):
            raise ValueError("Unknown supporting fact")
        for i, fact in enumerate(selected):
            if (fact.subject, fact.object) != tuple(e.expected_path[i : i + 2]):
                raise ValueError("Evidence is not a connected directed path")
        if set(e.source_document_ids) != {f.source_document_id for f in selected}:
            raise ValueError("Evaluation citations do not match facts")
        endpoint = next(x for x in fixture.entities if x.id == e.expected_path[-1])
        if normalize_name(e.expected_answer) != normalize_name(endpoint.name):
            raise ValueError("Expected answer does not name the path endpoint")


def safe_filename(name: str) -> bool:
    return re.fullmatch(r"[0-9]{3}_[a-z0-9_]+\.cypher", name) is not None
