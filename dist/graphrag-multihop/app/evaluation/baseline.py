"""Gold labels live here and in offline scripts only; runtime never imports evaluation."""

import statistics


def normalize_answer(value):
    if value is None:
        return None
    return sorted(" ".join(x.casefold().split()) for x in value.split(";"))


def measure(question, facts, response):
    required = {f["id"]: f for f in facts if f["id"] in question["supporting_fact_ids"]}
    chunks = response["retrieved_chunks"]
    covered = {
        fid
        for fid, f in required.items()
        if any(
            c["document_id"] == f["document_id"]
            and c["start"] <= f["start"]
            and c["end"] >= f["end"]
            and c["text"][f["start"] - c["start"] : f["end"] - c["start"]] == f["quote"]
            for c in chunks
        )
    }
    docs = set(question["required_document_ids"])
    found_docs = {c["document_id"] for c in chunks} & docs
    chain = bool(required) and covered == set(required)
    correct = normalize_answer(response["answer"]) == normalize_answer(question["expected_answer"])
    citation_count, correct_citations = len(response["citations"]), 0
    cited_facts = set()
    for cite in response["citations"]:
        grounded = any(
            c["chunk_id"] == cite["chunk_id"]
            and c["document_id"] == cite["document_id"]
            and c["start"] <= cite["start"] < cite["end"] <= c["end"]
            and c["text"][cite["start"] - c["start"] : cite["end"] - c["start"]] == cite["quote"]
            for c in chunks
        )
        matched = {
            fid
            for fid, f in required.items()
            if f["document_id"] == cite["document_id"]
            and f["start"] == cite["start"]
            and f["end"] == cite["end"]
            and f["quote"] == cite["quote"]
        }
        if grounded and matched:
            correct_citations += 1
            cited_facts |= matched
    supported = bool(required) and cited_facts == set(required) and correct
    return {
        "document_recall": len(found_docs) / len(docs) if docs else None,
        "precision": sum(c["document_id"] in docs for c in chunks) / len(chunks)
        if docs and chunks
        else (0 if docs else None),
        "required_evidence_coverage": len(covered) / len(required) if required else None,
        "complete_chain": chain if required else None,
        "exact_match": correct,
        "abstained": response["abstained"],
        "citation_count": citation_count,
        "correct_citations": correct_citations,
        "unsupported_answer": response["answer"] is not None and not supported,
        "covered_fact_ids": sorted(covered),
        "missing_fact_ids": sorted(set(required) - covered),
        "retrieved_document_ids": [c["document_id"] for c in chunks],
    }


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * p
    lo = int(position)
    return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (position - lo)


def aggregate(rows):
    def mean(key):
        values = [r[key] for r in rows if r[key] is not None]
        return statistics.mean(values) if values else None

    count = sum(r["citation_count"] for r in rows)
    return {
        "questions": len(rows),
        "document_recall": mean("document_recall"),
        "precision": mean("precision"),
        "required_evidence_coverage": mean("required_evidence_coverage"),
        "complete_chain_coverage": mean("complete_chain"),
        "answer_exact_match": mean("exact_match"),
        "abstention_rate": mean("abstained"),
        "citation_correctness": sum(r["correct_citations"] for r in rows) / count
        if count
        else None,
        "citation_count": count,
        "unsupported_answer_count": sum(r["unsupported_answer"] for r in rows),
        "latency_ms": {
            key: {
                "p50": percentile([r["latency_ms"][key] for r in rows], 0.5),
                "p95": percentile([r["latency_ms"][key] for r in rows], 0.95),
            }
            for key in ("query_embedding", "vector_retrieval", "end_to_end")
        },
    }
