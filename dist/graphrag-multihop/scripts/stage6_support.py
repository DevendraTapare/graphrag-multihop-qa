"""Stage 6 paths, append-only access audit, and historical preservation checks."""

import hashlib
import json
from datetime import UTC, datetime

from app.graph.fixtures import ROOT

OUT = ROOT / "reports/stage6"
DATA = ROOT / "data/stage6"
ALLOWED = {"README.md", "docs/PROJECT_ROADMAP.md"}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def access(action, path):
    with (OUT / "label_access.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "utc": datetime.now(UTC).isoformat(),
                    "action": action,
                    "path": str(path),
                    "actor": "Codex local offline evaluator",
                }
            )
            + "\n"
        )


def check_history():
    frozen = read("history_freeze.json")["files"]
    changed = [p for p, h in frozen.items() if digest((ROOT / p).read_bytes()) != h]
    if not (set(changed) <= ALLOWED):
        raise AssertionError(changed)
    return {"files": len(frozen), "changed": changed, "historical_results_unchanged": True}


def runtime_hashes():
    paths = [
        *(ROOT / "app").rglob("*.py"),
        ROOT / "uv.lock",
        ROOT / "scripts/stage6_runtime.py",
        ROOT / "scripts/build_stage6.py",
        ROOT / "scripts/stage6_dataset.py",
        ROOT / "scripts/evaluate_stage6.py",
        ROOT / "scripts/stage6_support.py",
        ROOT / "scripts/performance_stage6.py",
        ROOT / "scripts/recovery_stage6.py",
        ROOT / "scripts/stage6_benchmark.py",
        ROOT / "compose.stage6.yml",
        ROOT / "docs/STAGE6_EVALUATION_PROTOCOL.md",
        *DATA.glob("*.json"),
    ]
    return {
        p.relative_to(ROOT).as_posix(): digest(p.read_bytes())
        for p in sorted(paths)
        if p.name not in {"labels.json", "world.json"}
    }


def check_freeze():
    if not (runtime_hashes() == read("configuration_freeze.json")["files"]):
        raise AssertionError("Frozen runtime changed")
    check_history()
