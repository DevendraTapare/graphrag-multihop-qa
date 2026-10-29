"""Compare two completed real evaluations, excluding timings and memory samples."""

import json

from app.graph.fixtures import ROOT


def main():
    first = json.loads((ROOT / ".pytest_cache/stage3-final-first-evaluation.json").read_text())
    second = json.loads((ROOT / "reports/stage3/baseline_metrics.json").read_text())
    keys = [
        "id",
        "split",
        "hops",
        "top_k",
        "answer",
        "reason",
        "document_recall",
        "precision",
        "required_evidence_coverage",
        "complete_chain",
        "exact_match",
        "abstained",
        "citation_count",
        "correct_citations",
        "unsupported_answer",
        "covered_fact_ids",
        "missing_fact_ids",
        "retrieved_document_ids",
        "retrieved_chunk_ids",
        "scores",
    ]
    if not (first["configuration"]["corpus"] == second["configuration"]["corpus"]):
        raise AssertionError()
    if not (
        first["configuration"]["embedding_version"] == second["configuration"]["embedding_version"]
    ):
        raise AssertionError()

    def comparable(rows):
        return [{k: r[k] for k in keys} for r in rows]

    equal = comparable(first["queries"]) == comparable(second["queries"])
    result = {
        "dataset_version": second["dataset_version"],
        "corpus_build": second["configuration"]["corpus"]["build_id"],
        "embedding_version": second["configuration"]["embedding_version"],
        "query_comparisons": len(second["queries"]),
        "same_ranked_chunks_scores_answers_and_metrics": equal,
        "compared_fields": keys,
        "timings_excluded": True,
        "first_k5_end_to_end_ms": first["metrics"]["all"]["5"]["overall"]["latency_ms"][
            "end_to_end"
        ],
        "second_k5_end_to_end_ms": second["metrics"]["all"]["5"]["overall"]["latency_ms"][
            "end_to_end"
        ],
    }
    (ROOT / "reports/stage3/reproducibility.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not (equal):
        raise AssertionError(
            "Repeated real evaluation changed results; investigate before claiming repeatability"
        )


if __name__ == "__main__":
    main()
