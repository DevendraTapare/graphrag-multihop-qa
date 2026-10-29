"""Portfolio preparation without mutating the frozen research implementation/evidence."""

import hashlib
import json
from pathlib import Path

from app.graph.fixtures import ROOT

OUT = ROOT / "reports/stage7a"
RELEASE = ROOT / "dist/graphrag-multihop"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def check_research():
    files = read("research_freeze.json")["files"]
    changed = [p for p, h in files.items() if digest(ROOT / p) != h]
    assert not changed, changed
    return {"original_files": len(files), "changed": []}
