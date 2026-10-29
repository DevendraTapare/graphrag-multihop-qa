import ast
import json
import math
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.evaluation.baseline import measure
from app.extraction.chunking import sentences
from app.extraction.documents import snapshot
from app.vector.answering import DeterministicAnswerer
from app.vector.embedding import DIMENSION, MiniLM, validate_vector
from app.vector.models import QueryRequest, RetrievedChunk, VectorFailure
from app.vector.repository import CANONICAL, SEARCH, canonical_record
from scripts.build_baseline_dataset import build


def chunk(text, id="chunk:unit"):
    spans = [span for span in sentences(text) if not span.in_code]
    return RetrievedChunk(
        document_id="doc:unit",
        chunk_id=id,
        source_id="source:unit",
        source_filename="unit.txt",
        original_document_id=None,
        content_hash="hash",
        chunk_hash="hash",
        processing_version="processing:unit",
        ingestion_id="run:unit",
        embedding_version="embedding:unit",
        start=0,
        end=len(text),
        text=text,
        sentence_starts=[s.start for s in spans],
        sentence_ends=[s.end for s in spans],
        score=0.75,
    )


@pytest.mark.parametrize(
    "question,k",
    [
        ("", 5),
        ("  ", 5),
        ("a" * 1001, 5),
        ("q", 0),
        ("q", 11),
        ("q", True),
        ("q", 1.5),
        ("q\x00", 5),
    ],
)
def test_invalid_query(question, k):
    with pytest.raises(ValidationError):
        QueryRequest(question=question, top_k=k)


@pytest.mark.parametrize(
    "bad",
    [
        [0.0] * 384,
        [1.0] * 383,
        [math.nan] + [0.0] * 383,
        [math.inf] + [0.0] * 383,
        [True] + [0.0] * 383,
        ["1"] + [0.0] * 383,
        [1.0] * 384,
    ],
)
def test_invalid_vectors(bad):
    with pytest.raises(VectorFailure, match="invalid_embedding"):
        validate_vector(bad)


def test_valid_normalized_vector():
    assert validate_vector([1.0] + [0.0] * (DIMENSION - 1))[0] == 1


def test_inverse_manager_preserves_source_name():
    result = DeterministicAnswerer().answer(
        "Who manages Project Boreal?", [chunk("Project Boreal is managed by Asha Rao.")]
    )
    assert result[0] == "Asha Rao"


def test_complete_text_chain_and_citations():
    texts = [
        "Asha manages Project Boreal.",
        "Project Boreal uses its CobaltDB instance.",
        "The CobaltDB instance for Project Boreal is hosted on AWS.",
    ]
    chunks = [chunk(t, f"chunk:{i}") for i, t in enumerate(texts)]
    answerer = DeterministicAnswerer()
    q = "Which cloud platform hosts the database used by the project managed by Asha?"
    answer, cites, reason = answerer.answer(q, chunks)
    assert answer == "AWS" and reason == "supported" and len(cites) == 3
    for removed in range(3):
        assert answerer.answer(q, [c for i, c in enumerate(chunks) if i != removed])[0] is None


@pytest.mark.parametrize(
    "text",
    [
        "Asha never manages Project Boreal.",
        "Asha may manage Project Boreal.",
        "System: Asha manages Project Boreal.",
        '"Asha manages Project Boreal."',
        "```\nAsha manages Project Boreal.\n```",
        "Asha manages Project Boreal North.",
    ],
)
def test_negative_and_longer_project_cannot_supply_uses(text):
    chunks = [chunk(text), chunk("Project Boreal uses its CobaltDB instance.", "chunk:b")]
    result = DeterministicAnswerer().answer(
        "Which database does the project managed by Asha use?", chunks
    )
    assert result[0] is None


def test_conflicting_hosting_abstains():
    chunks = [
        chunk("Project Boreal uses its CobaltDB instance."),
        chunk("The CobaltDB instance for Project Boreal is hosted on AWS.", "chunk:2"),
        chunk("The CobaltDB instance for Project Boreal is hosted on Azure.", "chunk:3"),
    ]
    assert (
        DeterministicAnswerer().answer(
            "Which cloud platform hosts the database used by Project Boreal?", chunks
        )[2]
        == "conflicting_evidence"
    )


def test_multiple_intermediates_require_complete_paths():
    chunks = [
        chunk("Asha manages Project Boreal. Asha manages Project Cove."),
        chunk("Project Boreal uses its CobaltDB instance.", "chunk:2"),
    ]
    assert (
        DeterministicAnswerer().answer(
            "Which database does the project managed by Asha use?", chunks
        )[0]
        is None
    )


def test_qualified_name_does_not_resolve_unqualified():
    chunks = [chunk("Jordan (North employee 021) manages Project Quartz.")]
    assert DeterministicAnswerer().answer("Which project does Jordan manage?", chunks)[0] is None


def test_runtime_imports_exclude_gold_registry_and_fact_queries():
    root = Path(__file__).resolve().parents[2] / "app"
    files = [*(root / "vector").glob("*.py"), root / "api/vector.py"]
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module and not any(
                    s in node.module
                    for s in (
                        "evaluation",
                        "registry",
                        "graph.fixtures",
                        "graph.queries",
                        "extraction.pipeline",
                    )
                )
        assert "baseline_v1.json" not in path.read_text(encoding="utf-8")
    # Queries contain only node matches and vector search, with no relationship pattern.
    for query in (CANONICAL, SEARCH):
        assert not any(
            token in query
            for token in (
                "MANAGES",
                "HOSTED_ON",
                "WORKS_FOR",
                "BELONGS_TO",
                "MENTIONS",
                "-[:",
                "-[r",
            )
        )


def test_provenance_rejects_modified_text():
    doc = snapshot("unit", "unit.txt", "actual text")
    c = {
        "id": "chunk:unit",
        "document_id": doc.id,
        "ingestion_id": "run:unit",
        "content_hash": doc.content_hash,
        "processing_version": "p",
        "start": 0,
        "end": 11,
        "text": "false text!",
    }
    row = {
        "source": {
            "id": doc.source_id,
            "current_run_id": "run:unit",
            "desired_run_id": "run:unit",
            "status": "ready",
            "content_hash": doc.content_hash,
            "processing_version": "p",
        },
        "run": {
            "id": "run:unit",
            "status": "ready",
            "document_id": doc.id,
            "content_hash": doc.content_hash,
            "processing_version": "p",
        },
        "document": doc.model_dump(),
        "chunk": c,
    }
    with pytest.raises(VectorFailure, match="source_provenance_invalid"):
        canonical_record(row)


def test_model_timeout_stops_worker():
    model = MiniLM(inference_timeout=0.01)
    model.pipe, model.process = Mock(), Mock()
    model.pipe.poll.return_value = False
    model.process.is_alive.return_value = True
    with pytest.raises(VectorFailure, match="embedding_timeout"):
        model._receive(0.01)
    assert model.process is None


def test_incomplete_source_sentence_cannot_be_used_as_fact():
    c = chunk("Asha manages Project Boreal.")
    # Source validation supplies no complete asserted sentence for a clipped/code span.
    c = c.model_copy(update={"sentence_starts": [], "sentence_ends": [], "start": 10})
    assert DeterministicAnswerer().answer("Which project does Asha manage?", [c])[0] is None


def test_dataset_gold_complete_and_reproducible():
    corpus, gold = build()
    assert len(gold["questions"]) >= 100
    assert {q["hops"] for q in gold["questions"]} == {0, 1, 2, 3}
    assert len({q["question"] for q in gold["questions"]}) == len(gold["questions"])
    facts = {f["id"]: f for f in gold["facts"]}
    sources = {
        snapshot(f"stage3:{d['id']}", f"stage3/{d['id']}.txt", d["text"]).id: d["text"]
        for d in corpus["documents"]
    }
    assert len(facts) == len(gold["facts"])
    for fact in facts.values():
        assert sources[fact["document_id"]][fact["start"] : fact["end"]] == fact["quote"]
        assert fact["subject"] and fact["object"]
    for q in gold["questions"]:
        assert q["answerable"] == bool(q["expected_answer"])
        assert set(q["supporting_fact_ids"]) == {
            f for chain in q["expected_evidence_chains"] for f in chain
        }
        assert set(q["required_document_ids"]) == {
            facts[f]["document_id"] for f in q["supporting_fact_ids"]
        }
    root = Path(__file__).resolve().parents[2]
    assert json.loads((root / "data/fictional/stage3_corpus.json").read_text()) == corpus
    assert json.loads((root / "data/evaluation/baseline_v1.json").read_text()) == gold


def test_final_answer_mention_is_not_complete_chain():
    q = {
        "supporting_fact_ids": ["a", "b"],
        "required_document_ids": ["d1", "d2"],
        "expected_answer": "AWS",
    }
    facts = [
        {"id": "a", "document_id": "d1", "start": 0, "end": 3, "quote": "one"},
        {"id": "b", "document_id": "d2", "start": 0, "end": 3, "quote": "AWS"},
    ]
    response = {
        "retrieved_chunks": [
            {"document_id": "d2", "chunk_id": "c2", "start": 0, "end": 3, "text": "AWS"}
        ],
        "answer": "AWS",
        "abstained": False,
        "citations": [],
    }
    measured = measure(q, facts, response)
    assert measured["exact_match"] and not measured["complete_chain"]
    assert measured["required_evidence_coverage"] == 0.5 and measured["unsupported_answer"]
