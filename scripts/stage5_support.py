"""Stage 5 audit helpers; historical graph and reports are read-only."""

import hashlib
import json
import re
import zipfile
from datetime import UTC, datetime

from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from app.graph.fixtures import ROOT
from scripts.stage4_support import check_graph_snapshot

OUT = ROOT / "reports/stage5"
CHANGES = {
    ".env.example",
    "README.md",
    "app/core/config.py",
    "app/main.py",
    "docs/PROJECT_ROADMAP.md",
    "reports/README.md",
    "tests/unit/test_api.py",
}


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def freeze_history():
    assert not (OUT / "history_freeze.json").exists()
    manifest = (ROOT / "reports/stage4/FILE_MANIFEST.md").read_text(encoding="utf-8")
    paths = set(json.loads((ROOT / "reports/stage4/baseline_freeze.json").read_text())["files"])
    paths.update(re.findall(r"\| `([^`]+)` \|", manifest))
    db = GraphDatabaseClient(Settings())
    try:
        snapshot = check_graph_snapshot(db)
    finally:
        db.close()
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT / "frozen_stage4.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(ROOT / path, path)
    save(
        "history_freeze.json",
        {
            "created_at_utc": datetime.now(UTC).isoformat(),
            "files": {
                p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(paths)
            },
            "historical_graph": snapshot,
            "settings": Settings().model_dump(mode="json", exclude={"neo4j_password"}),
        },
    )
    return {"preserved_files": len(paths), "historical_graph": snapshot}


def check_history():
    frozen = read("history_freeze.json")
    changed = [
        p
        for p, h in frozen["files"].items()
        if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h
    ]
    assert set(changed) <= CHANGES, changed
    settings = Settings().model_dump(mode="json", exclude={"neo4j_password"})
    assert {k: settings[k] for k in frozen["settings"]} == frozen["settings"]
    return {
        "preserved_files": len(frozen["files"]),
        "allowed_integration_changes": changed,
        "historical_results_unchanged": True,
    }


def aligned_snapshot(db):
    def execute(query):
        return db.execute(query, timeout=30)

    result = {
        "nodes": execute(
            "MATCH (n:GraphNode) RETURN properties(n) AS properties, "
            "labels(n) AS labels ORDER BY n.id"
        ),
        "edges": execute(
            "MATCH (a:GraphNode)-[r]->(b:GraphNode) RETURN a.id AS source, "
            "b.id AS target,type(r) AS kind,properties(r) AS properties ORDER BY r.id"
        ),
        "sources": execute(
            "MATCH (s:IngestionSource) RETURN properties(s) AS properties ORDER BY s.id"
        ),
        "runs": execute("MATCH (i:Ingestion) RETURN properties(i) AS properties ORDER BY i.id"),
        "vectors": execute(
            "MATCH (e:ChunkEmbedding) RETURN properties(e) AS properties ORDER BY e.id"
        ),
    }
    for row in result["nodes"]:
        row["labels"].sort()
    for key in ("sources", "runs"):
        for row in result[key]:
            for field in ("lock_marker", "claim_token"):
                row["properties"].pop(field, None)
    return result


if __name__ == "__main__":
    print(json.dumps(freeze_history(), indent=2))
