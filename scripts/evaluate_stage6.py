"""Frozen challenge scorer. Gold is read only here and never passed to services."""

import argparse
import csv
import json
import platform
import time
from collections import Counter

import psutil

from app.evaluation.baseline import measure, normalize_answer, percentile
from app.vector.embedding import MODEL, REVISION
from scripts.evaluate_stage5 import graph_chain, normalize
from scripts.stage6_runtime import Components
from scripts.stage6_support import DATA, OUT, access, check_freeze, digest, read, save

MODES = ("vector_only", "graph_only", "hybrid_graph_vector")


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in {"latency_ms", "request_id"}}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def summary(rows):
    positives = [r for r in rows if r["answerable"]]
    negatives = [r for r in rows if not r["answerable"]]
    count = sum(r["citation_count"] for r in rows)

    def avg(key, subset=rows):
        vals = [r[key] for r in subset if r[key] is not None]
        return sum(vals) / len(vals) if vals else None

    return {
        "questions": len(rows),
        "answerable": len(positives),
        "exact_match_count": sum(r["exact_match"] for r in rows),
        "answer_exact_match": avg("exact_match"),
        "answerable_accuracy": avg("exact_match", positives),
        "required_evidence_recall": avg("required_evidence_coverage", positives),
        "complete_chain_coverage": avg("complete_chain", positives),
        "validated_graph_chain_coverage": avg("validated_graph_chain", positives),
        "citation_count": count,
        "incorrect_citations": count - sum(r["correct_citations"] for r in rows),
        "citation_correctness": sum(r["correct_citations"] for r in rows) / count
        if count
        else None,
        "source_invalid_citations": sum(r["source_invalid_citations"] for r in rows),
        "unsupported_answers": sum(r["unsupported_answer"] for r in rows),
        "false_abstentions": sum(r["abstained"] for r in positives),
        "false_abstention_rate": avg("abstained", positives),
        "correct_unanswerable_abstention_rate": avg("abstained", negatives),
        "wrong_entity_resolutions": sum(r["wrong_entity_resolution"] for r in rows),
        "entity_resolutions_checked": sum(r["entity_resolution_checked"] for r in rows),
        "construction_complete_rate": avg("construction_complete", positives),
        "failure_causes": dict(Counter(r["failure_cause"] for r in rows)),
        "latency_ms": {
            "p50": percentile([r["wall_ms"] for r in rows], 0.5),
            "p95": percentile([r["wall_ms"] for r in rows], 0.95),
        },
    }


def cause(q, response, metrics, construction):
    if metrics["exact_match"]:
        return "correct_answer" if q["answerable"] else "correct_abstention"
    reason = response.get("reason", "")
    if "unsupported" in reason:
        return "unsupported_grammar"
    if "ambiguous" in reason:
        return "ambiguous_entity_resolution"
    if "not_found" in reason or "unknown" in reason:
        return "missing_entity"
    if not construction:
        return "unsupported_extraction_pattern"
    if "conflict" in reason:
        return "conflicting_graph_facts"
    if "invalid" in reason or "provenance" in reason:
        return "source_provenance_failure"
    if "intermediate" in reason or "complete_path" in reason:
        return "missing_intermediate_evidence"
    if not metrics["complete_chain"]:
        return "insufficient_vector_evidence"
    return "deterministic_answerer_limitation"


def main(run):
    check_freeze()
    assert not (OUT / f"challenge_{run}.json").exists(), "Never overwrite a scored run"
    path = DATA / "labels.json"
    assert digest(path.read_bytes()) == read("label_seal.json")["sha256"]
    access(f"grading read: {run}; no tuning", path)
    gold = json.loads(path.read_text())
    source_docs = {d["id"]: d for d in json.loads((DATA / "sources.json").read_text())}
    snapshot = read("challenge_snapshot.json")
    accepted_spans = set()
    for e in snapshot["edges"]:
        p = e["properties"]
        for f in gold["facts"]:
            if p.get("source_document_id") == f["document_id"] and e["kind"] == f["predicate"]:
                if (p.get("quote"), p.get("evidence_start"), p.get("evidence_end")) == (
                    f["quote"],
                    f["start"],
                    f["end"],
                ):
                    accepted_spans.add(f["id"])
    components = Components()
    rows = []
    try:
        started = time.perf_counter()
        components.model.encode(["Stage six local model warmup."])
        cold = (time.perf_counter() - started) * 1000
        calibration = [q for q in gold["questions"] if q["split"] == "calibration"]
        for mode in MODES:
            components.query(mode, calibration[1]["question"])
        for mode in MODES:
            for q in gold["questions"]:
                started = time.perf_counter()
                response = components.query(mode, q["question"])
                wall = (time.perf_counter() - started) * 1000
                normalized = normalize(response, mode)
                metrics = measure(q, gold["facts"], normalized)
                construction = (
                    set(q["supporting_fact_ids"]) <= accepted_spans if q["answerable"] else None
                )
                invalid_cites = 0
                for cite in response["citations"]:
                    doc = source_docs.get(cite["document_id"])
                    if not doc or doc["text"][cite["start"] : cite["end"]] != cite["quote"]:
                        invalid_cites += 1
                resolution = response.get("resolution") or {}
                resolved = resolution.get("status") == "resolved" and q["start_surface"] is not None
                entity = (
                    components.graph.pipeline.registry.entries.get(resolution.get("canonical_id"))
                    if resolved
                    else None
                )
                wrong = bool(
                    resolved
                    and (
                        entity is None
                        or normalize_answer(entity.entity.name)
                        != normalize_answer(q["start_surface"])
                    )
                )
                row = {
                    "id": q["id"],
                    "question": q["question"],
                    "mode": mode,
                    "split": q["split"],
                    "hops": q["hops"],
                    "answerable": q["answerable"],
                    "tags": q["tags"],
                    "expected_answer": q["expected_answer"],
                    **metrics,
                    "construction_complete": construction,
                    "wall_ms": wall,
                    "validated_graph_chain": graph_chain(q, gold["facts"], response)
                    if mode != "vector_only"
                    else None,
                    "source_invalid_citations": invalid_cites,
                    "entity_resolution_checked": bool(resolved),
                    "wrong_entity_resolution": wrong,
                    "failure_cause": cause(q, response, metrics, construction),
                    "response": response,
                }
                rows.append(row)
            print(f"{run}: {mode} completed {len(gold['questions'])} questions", flush=True)
        summaries = {}
        for mode in MODES:
            mrows = [r for r in rows if r["mode"] == mode]
            summaries[mode] = {
                split: {
                    "overall": summary(selected := [r for r in mrows if r["split"] == split]),
                    "by_hop": {
                        str(h): summary([r for r in selected if r["hops"] == h and r["answerable"]])
                        for h in (1, 2, 3)
                    },
                    "by_tag": {
                        t: summary([r for r in selected if t in r["tags"]])
                        for t in sorted({t for r in selected for t in r["tags"]})
                    },
                }
                for split in ("calibration", "document_held_out", "template_held_out")
            }
            summaries[mode]["final"] = summary([r for r in mrows if r["split"] != "calibration"])
        save(
            f"challenge_{run}.json",
            {
                "protocol": "controlled-challenge-v1",
                "configuration": {
                    "top_k": 5,
                    "max_hops": 3,
                    "model": MODEL,
                    "revision": REVISION,
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "logical_cpus": psutil.cpu_count(),
                    "physical_cpus": psutil.cpu_count(logical=False),
                    "memory_bytes": psutil.virtual_memory().total,
                    "cold_model_first_encode_ms": cold,
                    "runtime_freeze_sha256": digest(
                        (OUT / "configuration_freeze.json").read_bytes()
                    ),
                    "neo4j": components.db.execute(
                        "CALL dbms.components() YIELD versions RETURN versions"
                    )[0],
                },
                "summary": summaries,
                "queries": rows,
            },
        )
    finally:
        components.close()


def report():
    first, second = read("challenge_run1.json"), read("challenge_run2.json")
    differences = [
        a["mode"] + ":" + a["id"]
        for a, b in zip(first["queries"], second["queries"], strict=True)
        if stable({k: v for k, v in a.items() if k != "wall_ms"})
        != stable({k: v for k, v in b.items() if k != "wall_ms"})
    ]
    final = [r for r in second["queries"] if r["split"] != "calibration"]
    byid = {q: {r["mode"]: r for r in final if r["id"] == q} for q in {r["id"] for r in final}}
    value = {
        "hybrid_only_correct": [],
        "graph_only_correct": [],
        "vector_only_correct": [],
        "hybrid_introduced_error": [],
    }
    for q, modes in sorted(byid.items()):
        correct = {m for m, r in modes.items() if r["exact_match"] and r["answerable"]}
        for mode, name in zip(
            MODES, ("vector_only_correct", "graph_only_correct", "hybrid_only_correct"), strict=True
        ):
            if correct == {mode}:
                value[name].append(q)
        if modes["graph_only"]["exact_match"] and not modes["hybrid_graph_vector"]["exact_match"]:
            value["hybrid_introduced_error"].append(q)
    save(
        "challenge_results.json",
        {
            "label": "NEW CONTROLLED CHALLENGE SET",
            "final_questions": len(byid),
            "summary": second["summary"],
            "hybrid_value": value,
            "reproducibility": {"comparisons": len(second["queries"]), "differences": differences},
            "queries": second["queries"],
        },
    )
    with (OUT / "challenge_results.csv").open("w", newline="", encoding="utf-8") as handle:
        keys = [
            "id",
            "mode",
            "split",
            "hops",
            "answerable",
            "expected_answer",
            "exact_match",
            "construction_complete",
            "required_evidence_coverage",
            "complete_chain",
            "validated_graph_chain",
            "citation_count",
            "correct_citations",
            "unsupported_answer",
            "abstained",
            "failure_cause",
            "wall_ms",
        ]
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(second["queries"])
    lines = [
        "# All failed or abstained challenge examples",
        "",
        "Both original scored runs retain every response, including correct abstentions. "
        "No final-set tuning occurred.",
        "",
    ]
    for r in second["queries"]:
        if not r["exact_match"] or r["abstained"]:
            lines.extend(
                [
                    f"## {r['mode']} / {r['id']} / {r['split']}",
                    "",
                    r["question"],
                    "",
                    f"Expected: {r['expected_answer']!r}; actual: {r['response']['answer']!r}.",
                    f"Cause: {r['failure_cause']}; runtime reason: {r['response']['reason']}; "
                    f"construction complete: {r['construction_complete']}; "
                    f"missing evidence: {r['missing_fact_ids']}.",
                    "",
                ]
            )
    (OUT / "error_analysis.md").write_text("\n".join(lines), encoding="utf-8")
    assert not differences, differences
    print(
        json.dumps(
            {
                "final_questions": len(byid),
                "deterministic_comparisons": len(second["queries"]),
                "hybrid_value": value,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", choices=["run1", "run2", "report"])
    args = parser.parse_args()
    report() if args.run == "report" else main(args.run)
