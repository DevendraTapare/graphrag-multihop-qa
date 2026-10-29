"""Verify all regressions and write the Stage 6 change inventory without changing history."""

import json
import os
import shutil
import xml.etree.ElementTree as ET

from app.extraction.registry import EntityRegistry
from app.graph.fixtures import ROOT
from app.graph.schema import Label
from scripts.check_ci_results import check
from scripts.stage5_support import aligned_snapshot
from scripts.stage6_benchmark import historical_databases
from scripts.stage6_runtime import Components
from scripts.stage6_support import (
    DATA,
    OUT,
    access,
    check_freeze,
    check_history,
    digest,
    read,
    save,
)
from scripts.verify_aligned import snapshot_digest


def inventory():
    old = read("history_freeze.json")["files"]
    files = {}
    for folder, directories, names in os.walk(ROOT):
        directories[:] = [
            d
            for d in directories
            if d not in {".venv", ".git", ".codex", ".pytest_cache", ".ruff_cache", "__pycache__"}
        ]
        for name in names:
            p = ROOT / folder / name
            relative = p.relative_to(ROOT).as_posix()
            if (
                (name.startswith(".env") and name != ".env.example")
                or p.suffix in {".pyc", ".log", ".xml"}
                or name.endswith("process.json")
                or relative == "reports/stage6/FILE_MANIFEST.md"
            ):
                continue
            files[relative] = digest(p.read_bytes())
    changed = sorted(p for p, h in old.items() if files.get(p) != h)
    new = sorted(set(files) - set(old))
    lines = [
        "# Stage 6 file inventory",
        "",
        "## Changed existing files",
        "",
        "| File | SHA-256 |",
        "| --- | --- |",
    ]
    lines += [f"| `{p}` | `{files[p]}` |" for p in changed]
    lines += ["", "## New files", "", "| File | SHA-256 |", "| --- | --- |"]
    lines += [f"| `{p}` | `{files[p]}` |" for p in new]
    lines += [
        "| `reports/stage6/FILE_MANIFEST.md` | Self hash omitted |",
        "",
        f"{len(changed)} existing files changed; {len(new) + 1} new files.",
        "",
        "Credentials, caches, logs and JUnit XML are excluded. "
        "All 241 previous paths remain present.",
    ]
    (OUT / "FILE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"changed_existing": changed, "new_file_count": len(new) + 1}


def main():
    check_freeze()
    path = ROOT / "reports/stage6-tests.xml"
    check(path)
    cases = list(ET.parse(path).getroot().iter("testcase"))
    old_cases = list(ET.parse(ROOT / "reports/stage5-tests.xml").getroot().iter("testcase"))
    ids = {(c.attrib["classname"], c.attrib["name"]) for c in cases}
    previous = {(c.attrib["classname"], c.attrib["name"]) for c in old_cases}
    assert len(previous) == 412 and previous <= ids, "Historical test cases missing"
    attempts = read("regression_attempts.json")
    attempts["attempt2"] = {
        "status": "passed",
        "passed": len(cases),
        "failed": 0,
        "skipped": 0,
        "duration_seconds": sum(
            float(s.attrib.get("time", 0)) for s in ET.parse(path).getroot().iter("testsuite")
        ),
        "junit": "reports/stage6-tests.xml",
        "junit_sha256": digest(path.read_bytes()),
        "environment": "Unused Stage 6 database stopped throughout full rerun; "
        "same runtime, timeouts, pool size and assertions",
    }
    attempts["attempt1"]["junit_sha256"] = digest(
        (ROOT / "reports/stage6-tests-attempt1.xml").read_bytes()
    )
    for source, target in (
        (".pytest_cache/stage6-tests.log", "regression_attempt1.log"),
        (".pytest_cache/stage6-load.log", "load_driver.log"),
    ):
        origin, destination = ROOT / source, OUT / target
        if destination.exists():
            assert destination.read_bytes() == origin.read_bytes()
        else:
            shutil.copyfile(origin, destination)
    attempts["attempt1"]["log"] = "reports/stage6/regression_attempt1.log"
    attempts["attempt1"]["log_sha256"] = digest((OUT / "regression_attempt1.log").read_bytes())
    save("regression_attempts.json", attempts)
    databases = historical_databases()
    assert databases == read("historical_databases_before.json")
    challenge = Components()
    try:
        current = snapshot_digest(aligned_snapshot(challenge.db))
        assert current == read("build_manifest.json")["snapshot_sha256"]
        registry = EntityRegistry(DATA / "registry.json")
        stored = {
            r["id"]
            for r in challenge.db.execute(
                "MATCH (n:GraphNode) WHERE n.id IN $ids RETURN n.id AS id",
                {"ids": list(registry.entries)},
            )
        }
    finally:
        challenge.close()
    sources = {d["id"]: d for d in json.loads((DATA / "sources.json").read_text())}
    access("final source-span and identity audit of sealed labels; no tuning", DATA / "labels.json")
    labels = json.loads((DATA / "labels.json").read_text())
    for fact in labels["facts"]:
        assert sources[fact["document_id"]]["text"][fact["start"] : fact["end"]] == fact["quote"]
    assert digest((DATA / "labels.json").read_bytes()) == read("label_seal.json")["sha256"]
    mappings, grouped = [], {}
    for mention in read("build_manifest.json")["source_grounded_mentions"]:
        options = registry.candidates(Label(mention["type"]), mention["mention"])
        ids_for_mention = [e.entity.id for e in options]
        mappings.append({**mention, "candidate_ids": ids_for_mention})
        if len(ids_for_mention) == 1:
            grouped.setdefault(ids_for_mention[0], []).append(mention)
    save(
        "identity_audit.json",
        {
            "stored_registry_entities": len(stored),
            "original_registry_ids_stored": len(stored & set(EntityRegistry().entries)),
            "source_mentions_to_registry_candidates": mappings,
            "repeated_mentions_coalesced": sum(len(v) - 1 for v in grouped.values()),
            "ambiguous_mentions": sum(len(m["candidate_ids"]) > 1 for m in mappings),
            "coalescence_groups": {k: v for k, v in grouped.items() if len(v) > 1},
            "note": "Counts exact source-to-registry reuse, "
            "not externally verified identity merges",
        },
    )
    save(
        "challenge_integrity.json",
        {
            "snapshot_unchanged": True,
            "sha256": current,
            "label_source_spans_checked": len(labels["facts"]),
            "label_source_span_errors": 0,
            "label_seal_unchanged": True,
        },
    )
    totals = {
        "passed": len(cases),
        "unit": sum(".unit." in c.attrib["classname"] for c in cases),
        "integration": sum(".integration." in c.attrib["classname"] for c in cases),
        "skipped": 0,
        "failures": 0,
        "errors": 0,
        "previous_regressions_preserved": len(previous),
        "historical_files": check_history(),
        "databases": databases,
        "runtime_frozen": True,
        "hosted_ci": "UNVERIFIED",
        "initial_attempt_failures_preserved": 1,
    }
    save("test_results.json", totals)
    access("read derived scored labels for final verification", OUT / "challenge_results.json")
    result = read("challenge_results.json")
    assert not result["reproducibility"]["differences"]
    assert len(read("load_results.json")["results"]) == 15
    assert read("recovery_results.json")["http_ready_recovered"] == 200
    assert read("build_manifest.json")["provenance_failures"] == 0
    changes = inventory()
    print(json.dumps({**totals, **changes}, indent=2))


if __name__ == "__main__":
    main()
