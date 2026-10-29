"""Record full regressions, exact repeated evaluation, and historical preservation."""

import hashlib
import json
import os
import xml.etree.ElementTree as ET

from app.aligned.components import AlignedComponents
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from app.graph.fixtures import ROOT
from scripts.evaluate_stage5 import FILENAMES, MODES, runtime_hashes
from scripts.stage4_support import check_graph_snapshot
from scripts.stage5_support import OUT, aligned_snapshot, check_history, read, save
from scripts.verify_aligned import snapshot_digest


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in {"latency_ms", "request_id"}}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def inventory():
    original = read("history_freeze.json")["files"]
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
            current[path.relative_to(ROOT).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    changed = sorted(p for p in original if current.get(p) != original[p])
    new = sorted(set(current) - set(original) - {"reports/stage5/FILE_MANIFEST.md"})
    lines = [
        "# Stage 5 file inventory",
        "",
        "## Changed existing files",
        "",
        "| File | SHA-256 |",
        "| --- | --- |",
    ]
    lines.extend(f"| `{p}` | `{current[p]}` |" for p in changed)
    lines += ["", "## New files", "", "| File | SHA-256 |", "| --- | --- |"]
    lines.extend(f"| `{p}` | `{current[p]}` |" for p in new)
    lines += [
        "| `reports/stage5/FILE_MANIFEST.md` | Self; omitted to avoid recursive hashing |",
        "",
        f"{len(changed)} changed existing files; {len(new) + 1} new shareable files.",
        "",
        "Local credentials, environments, caches, logs and JUnit XML are excluded. "
        "No dependency, historical fixture, migration or historical metric file changed.",
    ]
    (OUT / "FILE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    cases = list(ET.parse(ROOT / "reports/stage5-tests.xml").iter("testcase"))
    totals = {
        "total": len(cases),
        "passed": sum(
            not any(c.find(t) is not None for t in ("failure", "error", "skipped")) for c in cases
        ),
        "skipped": sum(c.find("skipped") is not None for c in cases),
        "failures": sum(c.find("failure") is not None for c in cases),
        "errors": sum(c.find("error") is not None for c in cases),
        "unit": sum("tests.unit." in c.get("classname", "") for c in cases),
        "integration": sum("tests.integration." in c.get("classname", "") for c in cases),
    }
    assert totals["skipped"] == totals["failures"] == totals["errors"] == 0
    assert totals["unit"] + totals["integration"] == totals["total"]
    original_cases = list(ET.parse(ROOT / "reports/stage4-tests.xml").iter("testcase"))
    identifiers = {(c.get("classname"), c.get("name")) for c in cases}
    assert {(c.get("classname"), c.get("name")) for c in original_cases} <= identifiers
    history = check_history()
    assert runtime_hashes() == read("runtime_freeze.json")["files"]
    db = GraphDatabaseClient(Settings())
    try:
        historical_snapshot = check_graph_snapshot(db)
    finally:
        db.close()
    components = AlignedComponents(Settings())
    try:
        aligned_sha = snapshot_digest(aligned_snapshot(components.db))
        assert aligned_sha == read("provenance_audit.json")["snapshot_sha256"]
    finally:
        components.close()
    differences, distributions = [], {}
    for mode in MODES:
        name = FILENAMES.get(mode, mode + "_metrics.json")
        first = json.loads((ROOT / ".pytest_cache/stage5-final-first" / name).read_text())
        second = read(name)
        assert len(first["queries"]) == len(second["queries"]) == 122
        differences.extend(
            {"mode": mode, "id": a["id"]}
            for a, b in zip(first["queries"], second["queries"], strict=True)
            if stable(a) != stable(b)
        )
        distributions[mode] = {
            "first": first["metrics"]["all"]["overall"]["latency_ms"],
            "second": second["metrics"]["all"]["overall"]["latency_ms"],
        }
    assert not differences, differences
    save(
        "determinism.json",
        {
            "runs": 2,
            "questions_per_mode": 122,
            "modes": list(MODES),
            "query_comparisons": 122 * len(MODES),
            "identical_non_timing_results": True,
            "difference_ids": differences,
            "latency_distributions": distributions,
            "aligned_snapshot_sha256": aligned_sha,
            "runtime_files": runtime_hashes(),
        },
    )
    save(
        "test_results.json",
        {
            **totals,
            "historical_cases_preserved": len(original_cases),
            "history": history,
            "historical_snapshot": historical_snapshot,
            "aligned_snapshot_sha256": aligned_sha,
            "junit": "reports/stage5-tests.xml",
            "runtime_freeze_valid": True,
        },
    )
    inventory()
    print(
        json.dumps(
            {
                **totals,
                "historical_cases_preserved": len(original_cases),
                "deterministic_query_comparisons": 122 * len(MODES),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
