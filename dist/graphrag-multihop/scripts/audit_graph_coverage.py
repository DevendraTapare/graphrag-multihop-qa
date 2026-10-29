"""Offline gold-to-frozen-source coverage audit; never creates identities or facts."""

import json

from app.extraction.registry import EntityRegistry
from app.graph.fixtures import ROOT
from app.graph.schema import DIRECTIONS, FactType
from scripts.stage4_support import OUT, read_json


def main():
    gold = json.loads((ROOT / "data/evaluation/baseline_v1.json").read_text(encoding="utf-8"))
    snapshot = read_json("graph_snapshot.json")
    corpus = json.loads((ROOT / "data/runtime/graph_corpus_v1.json").read_text())
    registry = EntityRegistry()
    accepted = [e for e in snapshot["edges"] if e["kind"] in {f.value for f in FactType}]
    rows = []
    for fact in gold["facts"]:
        source_type, target_type = DIRECTIONS[FactType(fact["predicate"])]
        subjects = [e.entity.id for e in registry.candidates(source_type, fact["subject"])]
        objects = [e.entity.id for e in registry.candidates(target_type, fact["object"])]
        matches = []
        for edge in accepted:
            props = edge["properties"]
            doc = props.get("source_document_id")
            if doc in corpus["curated_document_map"]:
                doc = corpus["curated_document_map"][doc]["document_id"]
            if (
                edge["source"] in subjects
                and edge["target"] in objects
                and edge["kind"] == fact["predicate"]
                and doc == fact["document_id"]
                and props.get("quote") == fact["quote"]
            ):
                matches.append(props["id"])
        rows.append(
            {
                "fact_id": fact["id"],
                "subject_registered": bool(subjects),
                "object_registered": bool(objects),
                "matching_assertion_ids": matches,
            }
        )
    result = {
        "gold_facts": len(rows),
        "facts_with_matching_graph_assertions": sum(
            bool(r["matching_assertion_ids"]) for r in rows
        ),
        "frozen_registry_entities": len(registry.entries),
        "facts": rows,
    }
    (OUT / "source_coverage.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "facts"}, indent=2))


if __name__ == "__main__":
    main()
