"""Offline graph grading; runtime never imports this package or evaluation labels."""

import statistics
from collections import Counter

from app.evaluation.baseline import measure, percentile

TIMINGS = (
    "parsing",
    "entity_linking",
    "traversal",
    "provenance",
    "selection",
    "revalidation",
    "generation",
    "end_to_end",
)


def normalized_response(response, corpus):
    # Curated documents duplicate Stage 2 snapshots already in the frozen corpus.
    # Map only verified identical original document text/hash; never map answers/facts.
    mapping = corpus["curated_document_map"]

    def normalize(item):
        item = dict(item)
        entry = mapping.get(item["document_id"])
        if entry and item.get("content_hash") == entry["content_hash"]:
            item["document_id"] = entry["document_id"]
        return item

    groups, aliases = {}, {}
    for native in response["evidence_chunks"]:
        chunk = normalize(native)
        key = (chunk["document_id"], chunk["start"], chunk["end"], chunk["text"])
        if key not in groups or chunk["chunk_id"] < groups[key]["chunk_id"]:
            groups[key] = chunk
    for native in response["evidence_chunks"]:
        chunk = normalize(native)
        key = (chunk["document_id"], chunk["start"], chunk["end"], chunk["text"])
        aliases[(chunk["document_id"], chunk["chunk_id"])] = groups[key]["chunk_id"]
    citations = {}
    for native in response["citations"]:
        cite = normalize(native)
        cite["chunk_id"] = aliases.get((cite["document_id"], cite["chunk_id"]), cite["chunk_id"])
        citations[(cite["document_id"], cite["start"], cite["end"], cite["quote"])] = cite
    return {
        "answer": response["answer"],
        "abstained": response["abstained"],
        "retrieved_chunks": list(groups.values()),
        "citations": list(citations.values()),
    }


def classify(question, response):
    reason = response["reason"]
    if not response["abstained"]:
        return ("none", "none")
    if reason == "unsupported_question_grammar":
        return "unsupported_question_grammar", "stage4_parser"
    if reason == "entity_ambiguous":
        return "ambiguous_entity_resolution", "registry_identity"
    if reason == "entity_not_found":
        return "missing_extraction_fact", "stage2_identity_coverage" if question[
            "answerable"
        ] else "expected_missing_or_unregistered_entity"
    if reason == "conflicting_answers":
        return "conflicting_graph_paths", "source_assertions"
    if response["diagnostics"].get("provenance_rejections", 0):
        return "incomplete_evidence_provenance", "source_validation"
    if reason in {"candidate_limit_exceeded", "answer_limit_exceeded", "requested_hop_limit"}:
        return "traversal_planning_failure", "stage4_bounds"
    return "missing_graph_edge", "stage2_graph_coverage"


def score(question, gold_facts, response, corpus, registry):
    normalized = normalized_response(response, corpus)
    measured = measure(question, gold_facts, normalized)  # Unchanged Stage 3 grading rules.
    intended_ids = set()
    if question["answerable"] and response["plan"]:
        plan = response["plan"]
        first_ids = {chain[0] for chain in question["expected_evidence_chains"]}
        for fact in gold_facts:
            if fact["id"] in first_ids:
                field = "subject" if plan["steps"][0]["direction"] == "outgoing" else "object"
                intended_ids.update(
                    e.entity.id for e in registry.candidates(plan["start_type"], fact[field])
                )
    resolution = response["resolution"] or {}
    assigned = resolution.get("canonical_id")
    wrong = bool(assigned and question["answerable"] and assigned not in intended_ids)
    wrong |= bool(assigned and question.get("reason") == "ambiguous_person")
    supported_facts = set()
    for path in response["reasoning_paths"]:
        if path["hop_count"] != question["hops"]:
            continue
        for step in path["steps"]:
            for cite in step["supports"]:
                mapped = corpus["curated_document_map"].get(cite["document_id"])
                document = (
                    mapped["document_id"]
                    if mapped and mapped["content_hash"] == cite["content_hash"]
                    else cite["document_id"]
                )
                supported_facts.update(
                    f["id"]
                    for f in gold_facts
                    if f["id"] in question["supporting_fact_ids"]
                    and f["predicate"] == step["relation"]
                    and f["document_id"] == document
                    and (f["start"], f["end"], f["quote"])
                    == (cite["start"], cite["end"], cite["quote"])
                )
    cause, origin = classify(question, response)
    if not measured["exact_match"] and not response["abstained"]:
        cause, origin = "answer_construction_failure", "stage4_generation"
    return {
        **measured,
        "error_cause": cause,
        "error_origin": origin,
        "resolved_assignment": bool(assigned),
        "incorrect_entity_link": wrong,
        "answerable_entity_outside_registry": question["answerable"] and not intended_ids,
        "resolution_status": resolution.get("status"),
        "expected_ambiguity": question.get("reason") == "ambiguous_person",
        "validated_graph_chain": bool(question["supporting_fact_ids"])
        and supported_facts == set(question["supporting_fact_ids"])
        if question["answerable"]
        else None,
        "provenance_edges_checked": response["diagnostics"].get("edges_checked", 0),
        "provenance_edges_rejected": response["diagnostics"].get("provenance_rejections", 0),
    }


def aggregate(rows):
    def mean(key):
        values = [r[key] for r in rows if r[key] is not None]
        return statistics.mean(values) if values else None

    citations = sum(r["citation_count"] for r in rows)
    checked = sum(r["provenance_edges_checked"] for r in rows)
    assigned = sum(r["resolved_assignment"] for r in rows)
    wrong = sum(r["incorrect_entity_link"] for r in rows)
    return {
        "questions": len(rows),
        "answer_exact_match": mean("exact_match"),
        "document_recall": mean("document_recall"),
        "precision": mean("precision"),
        "required_evidence_coverage": mean("required_evidence_coverage"),
        "complete_chain_coverage": mean("complete_chain"),
        "abstention_rate": mean("abstained"),
        "validated_graph_chain_coverage": mean("validated_graph_chain"),
        "citation_correctness": sum(r["correct_citations"] for r in rows) / citations
        if citations
        else None,
        "citation_count": citations,
        "unsupported_answer_count": sum(r["unsupported_answer"] for r in rows),
        "resolved_entity_assignments": assigned,
        "incorrect_entity_links": wrong,
        "entity_assignment_accuracy": 1 - wrong / assigned if assigned else None,
        "resolution_statuses": dict(Counter(r["resolution_status"] for r in rows)),
        "intended_ambiguous_cases": sum(r["expected_ambiguity"] for r in rows),
        "detected_ambiguous_cases": sum(
            r["expected_ambiguity"] and r["resolution_status"] == "ambiguous" for r in rows
        ),
        "answerable_outside_registry": sum(r["answerable_entity_outside_registry"] for r in rows),
        "provenance_edges_checked": checked,
        "provenance_failure_rate": sum(r["provenance_edges_rejected"] for r in rows) / checked
        if checked
        else None,
        "candidate_paths": sum(r["candidate_path_count"] for r in rows),
        "paths_discarded": sum(r["paths_discarded"] for r in rows),
        "failure_causes": dict(Counter(r["error_cause"] for r in rows)),
        "latency_ms": {
            k: {
                "p50": percentile([r["latency_ms"][k] for r in rows], 0.5),
                "p95": percentile([r["latency_ms"][k] for r in rows], 0.95),
            }
            for k in TIMINGS
        },
    }
