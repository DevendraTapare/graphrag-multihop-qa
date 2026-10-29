"""Offline post-freeze audit of challenge novelty and source/gold separation."""

import json
import re

from app.extraction.registry import EntityRegistry
from app.graph.fixtures import ROOT
from app.models.fixtures import normalize_name
from scripts.stage6_support import DATA, access, check_freeze, save


def template(question, registry):
    aliases = sorted(
        {(a, e.entity.label.value) for e in registry.data.entries for a in e.aliases},
        key=lambda x: (-len(x[0]), x),
    )
    for alias, label in aliases:
        question = re.sub(
            r"(?<!\w)" + re.escape(alias) + r"(?!\w)", f"<{label}>", question, flags=re.I
        )
    question = re.sub(r"Oriel Absent[A-Z]{2}|Unlisted Visitor s\d+", "<Person>", question)
    return " ".join(question.casefold().split())


def main():
    check_freeze()
    access(
        "offline post-freeze novelty and label/source separation audit; no tuning",
        DATA / "labels.json",
    )
    labels = json.loads((DATA / "labels.json").read_text())
    old = json.loads((ROOT / "data/evaluation/baseline_v1.json").read_text())
    registry = EntityRegistry(DATA / "registry.json")
    stage5 = EntityRegistry(ROOT / "data/runtime/stage5_registry.json")
    inherited = set(EntityRegistry().entries)
    new = {
        (e.entity.label.value, normalize_name(e.entity.name))
        for e in registry.data.entries
        if e.entity.id not in inherited
    }
    old_names = {(e.entity.label.value, normalize_name(e.entity.name)) for e in stage5.data.entries}
    reused_names = sorted(new & old_names)
    old_templates = {template(q["question"], stage5) for q in old["questions"]}
    challenge_templates = {template(q["question"], registry) for q in labels["questions"]}
    overlaps = sorted(old_templates & challenge_templates)
    sources = json.loads((DATA / "sources.json").read_text())
    source_ids = {d["source_id"] for d in sources}
    old_source_ids = set(
        json.loads((ROOT / "data/runtime/stage5_corpus.json").read_text())["source_ids"]
    )
    runtime_text = (DATA / "registry.json").read_text() + (DATA / "corpus.json").read_text()
    assert all(f["id"] not in runtime_text for f in labels["facts"])
    assert all(q["id"] not in runtime_text for q in labels["questions"])
    doc_split = {"calibration": set(), "document_held_out": set(), "template_held_out": set()}
    for d in sources:
        world = int(d["source_filename"].split("/")[1])
        split = (
            "calibration"
            if world >= 20
            else ("document_held_out" if world < 10 else "template_held_out")
        )
        doc_split[split].add(d["id"])
    assert all(
        not (a & b)
        for i, a in enumerate(doc_split.values())
        for j, b in enumerate(doc_split.values())
        if i != j
    )
    save(
        "novelty_audit.json",
        {
            "reused_stage5_identity_names": reused_names,
            "exact_entity_normalized_question_template_overlaps": overlaps,
            "old_templates": sorted(old_templates),
            "challenge_templates": sorted(challenge_templates),
            "reused_source_ids": sorted(source_ids & old_source_ids),
            "source_split_counts": {k: len(v) for k, v in doc_split.items()},
            "gold_ids_found_in_runtime_manifests": 0,
            "note": "Exact template normalization is a lexical audit, "
            "not semantic independence. "
            "Document holdout still uses related closed grammar families.",
        },
    )
    assert not reused_names and not overlaps and not (source_ids & old_source_ids)
    print(
        "Source IDs, new identity names, normalized question templates "
        "and label/runtime IDs audited"
    )


if __name__ == "__main__":
    main()
