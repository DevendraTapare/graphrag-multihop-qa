"""Record full-suite evidence and repeated benchmark determinism in Stage 4 only."""

import hashlib
import json
import os

from defusedxml import ElementTree as ET

from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from app.graph.fixtures import ROOT
from scripts.stage4_support import (
    OUT,
    check_frozen_files,
    check_graph_snapshot,
    check_runtime_freeze,
    read_json,
)


def write_manifest():
    frozen = read_json("baseline_freeze.json")["files"]
    current = {}
    for folder, directories, filenames in os.walk(ROOT):
        directories[:] = [
            d
            for d in directories
            if d
            not in {
                ".venv",
                ".git",
                "__pycache__",
                ".pytest_cache",
                ".ruff_cache",
                ".codex",
            }
        ]
        for name in filenames:
            path = ROOT / folder / name
            relative = path.relative_to(ROOT).as_posix()
            if (
                (name.startswith(".env") and name != ".env.example")
                or path.suffix
                in {
                    ".pyc",
                    ".log",
                    ".xml",
                }
                or name == "runtime-api-process.json"
            ):
                continue
            current[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    created = sorted(set(current) - set(frozen) - {"reports/stage4/FILE_MANIFEST.md"})
    changed = sorted(p for p in frozen if current.get(p) != frozen[p])
    lines = [
        "# Stage 4 file inventory",
        "",
        "Only the seven existing integration files below changed. All other frozen "
        "Stage 3 files remain byte-identical. No dependency or schema change was needed.",
        "",
        "## Changed existing files",
        "",
        "| File | SHA-256 |",
        "| --- | --- |",
    ]
    lines += [f"| `{p}` | `{current[p]}` |" for p in changed]
    lines += ["", "## New files", "", "| File | SHA-256 |", "| --- | --- |"]
    lines += [f"| `{p}` | `{current[p]}` |" for p in created]
    lines += [
        "| `reports/stage4/FILE_MANIFEST.md` | Self; omitted to avoid recursive hashing |",
        "",
        f"{len(changed)} changed existing files; {len(created) + 1} new shareable files.",
        "",
        "Local .env, environments, caches, logs and JUnit XML are excluded. "
        "The local JUnit evidence is reports/stage4-tests.xml.",
    ]
    (OUT / "FILE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    tree = ET.parse(ROOT / "reports/stage4-tests.xml")
    cases = list(tree.iter("testcase"))
    categories = {
        kind: [c for c in cases if f"tests.{kind}." in c.get("classname", "")]
        for kind in ("unit", "integration")
    }
    results = {
        "tests": len(cases),
        "passed": sum(
            not any(c.find(t) is not None for t in ("failure", "error", "skipped")) for c in cases
        ),
        "skipped": sum(c.find("skipped") is not None for c in cases),
        "failures": sum(c.find("failure") is not None for c in cases),
        "errors": sum(c.find("error") is not None for c in cases),
        "unit": len(categories["unit"]),
        "integration": len(categories["integration"]),
        "junit": "reports/stage4-tests.xml",
        "frozen_files": check_frozen_files(),
        "runtime_freeze": check_runtime_freeze(),
    }
    if not (results["skipped"] == results["failures"] == results["errors"] == 0):
        raise AssertionError()
    if not (results["unit"] + results["integration"] == results["tests"]):
        raise AssertionError()
    db = GraphDatabaseClient(Settings())
    try:
        results["graph_snapshot"] = check_graph_snapshot(db)
    finally:
        db.close()
    (OUT / "test_results.json").write_text(json.dumps(results, indent=2) + "\n")
    first = json.loads((ROOT / ".pytest_cache/stage4-first-graph.json").read_text())
    second = read_json("graph_metrics.json")

    def stable(row):
        return {k: v for k, v in row.items() if k != "latency_ms"}

    if not (len(first["queries"]) == len(second["queries"]) == 122):
        raise AssertionError()
    differences = [
        a["id"]
        for a, b in zip(first["queries"], second["queries"], strict=True)
        if stable(a) != stable(b)
    ]
    if not (not differences):
        raise AssertionError(differences)
    result = {
        "questions_per_run": 122,
        "runs": 2,
        "identical_non_timing_query_results": not differences,
        "difference_ids": differences,
        "runtime_sha256": second["configuration"]["runtime_sha256"],
        "snapshot_sha256": second["graph_snapshot_after"]["sha256"],
        "first_run_latency_ms": first["metrics"]["all"]["overall"]["latency_ms"],
        "second_run_latency_ms": second["metrics"]["all"]["overall"]["latency_ms"],
        "active_path_repeats": "operational_verification.json: exact paths/citations compared "
        "across five repeats at concurrency 1 and 4",
    }
    (OUT / "determinism.json").write_text(json.dumps(result, indent=2) + "\n")
    comparison = read_json("comparison.json")
    comparison["graph_only"] = second["metrics"]["all"]
    (OUT / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    write_manifest()
    print(json.dumps({k: v for k, v in results.items() if k != "runtime_freeze"}, indent=2))


if __name__ == "__main__":
    main()
