import json
from pathlib import Path

from app.extraction.documents import snapshot
from app.extraction.models import EntityCandidate
from app.extraction.pipeline import ExtractionPipeline
from app.graph.fixtures import ROOT


def read_cases(path: Path | None = None):
    return json.loads(
        (path or ROOT / "data/evaluation/extraction.json").read_text(encoding="utf-8")
    )["cases"]


def entity_key(entity: EntityCandidate):
    return entity.start, entity.end, entity.label.value


def metrics(tp, fp, fn):
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
    }


def evaluate(pipeline: ExtractionPipeline, cases=None):
    cases = cases if cases is not None else read_cases()
    results = []
    for case in cases:
        document = snapshot(f"evaluation:{case['id']}", f"{case['id']}.txt", case["text"])
        chunks, batch, validated = pipeline.extract(document)
        gold_entities = {(e["start"], e["end"], e["label"]): e for e in case["entities"]}
        predicted_entities = {entity_key(e): e for e in batch.entities}
        gold_relations = {
            (r["subject"], r["predicate"], r["object"], r["start"], r["end"])
            for r in case["relations"]
        }
        predicted_relations = {
            (
                f.subject_id,
                f.candidate.predicate.value,
                f.object_id,
                f.candidate.start,
                f.candidate.end,
            )
            for f in validated.facts
        }
        resolutions = {entity_key(e.candidate): e.canonical_id for e in validated.entities}
        correct_resolution = sum(
            key in predicted_entities and resolutions.get(key) == e["canonical_id"]
            for key, e in gold_entities.items()
        )
        wrong_merges = sum(
            key not in gold_entities or gold_entities[key]["canonical_id"] != id
            for key, id in resolutions.items()
        )
        provenance_correct = 0
        for fact in validated.facts:
            c = fact.candidate
            signature = (fact.subject_id, c.predicate.value, fact.object_id, c.start, c.end)
            if (
                signature in gold_relations
                and document.text[c.start : c.end] == c.evidence
                and fact.content_hash == document.content_hash
                and fact.processing_version == pipeline.version
                and c.source_document_id == document.id
                and any(chunk.id == c.source_chunk_id for chunk in chunks)
            ):
                provenance_correct += 1
        results.append(
            {
                "id": case["id"],
                "split": case["split"],
                "tags": case["tags"],
                "gold_entities": len(gold_entities),
                "gold_relations": len(gold_relations),
                "entity_tp": len(gold_entities.keys() & predicted_entities.keys()),
                "entity_fp": len(predicted_entities.keys() - gold_entities.keys()),
                "entity_fn": len(gold_entities.keys() - predicted_entities.keys()),
                "relation_tp": len(gold_relations & predicted_relations),
                "relation_fp": len(predicted_relations - gold_relations),
                "relation_fn": len(gold_relations - predicted_relations),
                "resolution_correct": correct_resolution,
                "incorrect_merges": wrong_merges,
                "unsupported_accepted_facts": len(predicted_relations - gold_relations),
                "accepted_facts": len(validated.facts),
                "provenance_correct": provenance_correct,
                "rejected_candidates": len(validated.rejections),
            }
        )

    def aggregate(rows):
        def total(key):
            return sum(r[key] for r in rows)

        gold = total("gold_entities")
        accepted = total("accepted_facts")
        return {
            "documents": len(rows),
            "gold_entity_examples": gold,
            "gold_relationship_examples": total("gold_relations"),
            "ambiguous_identity_cases": sum("ambiguous_identity" in r["tags"] for r in rows),
            "unsupported_cases": sum("unsupported" in r["tags"] for r in rows),
            "entities": metrics(total("entity_tp"), total("entity_fp"), total("entity_fn")),
            "relationships": metrics(
                total("relation_tp"), total("relation_fp"), total("relation_fn")
            ),
            "canonical_id_resolution_accuracy": total("resolution_correct") / gold
            if gold
            else None,
            "incorrect_merge_count": total("incorrect_merges"),
            "unsupported_accepted_fact_count": total("unsupported_accepted_facts"),
            "accepted_facts": accepted,
            "rejected_candidates": total("rejected_candidates"),
            "provenance_accuracy": total("provenance_correct") / accepted if accepted else None,
        }

    return {
        "processing_version": pipeline.version,
        "scope": "Synthetic controlled fictional text; not general-purpose extraction accuracy",
        "overall": aggregate(results),
        "calibration": aggregate([r for r in results if r["split"] == "calibration"]),
        "held_out": aggregate([r for r in results if r["split"] == "held_out"]),
        "cases": results,
    }
