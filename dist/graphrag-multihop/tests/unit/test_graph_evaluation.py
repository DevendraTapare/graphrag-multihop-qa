from app.evaluation.graph import normalized_response, score
from app.extraction.models import text_hash
from app.extraction.registry import EntityRegistry


def test_normalization_preserves_gold_rules_and_deduplicates_source_copies():
    text = "Morgan manages Project Atlas East."
    digest = text_hash(text)
    corpus = {
        "curated_document_map": {
            "doc:04": {"document_id": "autodoc:example", "content_hash": digest}
        }
    }
    chunks = [
        {
            "document_id": d,
            "chunk_id": c,
            "start": 0,
            "end": len(text),
            "text": text,
            "content_hash": digest,
        }
        for d, c in (("doc:04", "chunk:04"), ("autodoc:example", "autochunk:example"))
    ]
    citations = [
        {
            "document_id": c["document_id"],
            "chunk_id": c["chunk_id"],
            "start": 0,
            "end": len(text),
            "quote": text,
            "content_hash": digest,
        }
        for c in chunks
    ]
    response = {
        "evidence_chunks": chunks,
        "citations": citations,
        "answer": "Atlas East",
        "abstained": False,
    }
    normalized = normalized_response(response, corpus)
    assert len(normalized["retrieved_chunks"]) == len(normalized["citations"]) == 1
    assert normalized["citations"][0]["chunk_id"] == normalized["retrieved_chunks"][0]["chunk_id"]
    assert normalized["citations"][0]["document_id"] == "autodoc:example"
    assert response["evidence_chunks"][0]["document_id"] == "doc:04"
    corpus["curated_document_map"]["doc:04"]["content_hash"] = "different"
    assert len(normalized_response(response, corpus)["retrieved_chunks"]) == 2


def test_textual_coverage_is_not_a_validated_graph_path():
    q = {
        "answerable": True,
        "hops": 2,
        "expected_answer": "PostgreSQL",
        "supporting_fact_ids": ["f1", "f2"],
        "required_document_ids": ["doc:unit"],
        "expected_evidence_chains": [["f1", "f2"]],
    }
    text = "Morgan manages Project Atlas. Project Atlas uses PostgreSQL."
    first, second = text.split(". ")
    first += "."
    facts = [
        {"id": "f1", "document_id": "doc:unit", "start": 0, "end": len(first), "quote": first},
        {
            "id": "f2",
            "document_id": "doc:unit",
            "start": len(first) + 1,
            "end": len(text),
            "quote": second,
        },
    ]
    response = {
        "answer": None,
        "abstained": True,
        "reason": "missing_intermediate_evidence",
        "plan": None,
        "resolution": None,
        "reasoning_paths": [],
        "diagnostics": {},
        "citations": [],
        "evidence_chunks": [
            {
                "document_id": "doc:unit",
                "chunk_id": "c:unit",
                "start": 0,
                "end": len(text),
                "text": text,
                "content_hash": text_hash(text),
            }
        ],
    }
    row = score(q, facts, response, {"curated_document_map": {}}, EntityRegistry())
    assert row["complete_chain"] and not row["validated_graph_chain"]
    assert not row["exact_match"]
