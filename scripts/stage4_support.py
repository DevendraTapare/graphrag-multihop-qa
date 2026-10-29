"""Read-only freeze and graph-state checks shared by offline Stage 4 verification."""

import hashlib
import json

from app.core.config import Settings
from app.graph.fixtures import ROOT

OUT = ROOT / "reports/stage4"
INTEGRATION_CHANGES = {
    ".env.example",
    "README.md",
    "app/core/config.py",
    "app/main.py",
    "docs/PROJECT_ROADMAP.md",
    "reports/README.md",
    "tests/unit/test_api.py",
}


def read_json(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def check_frozen_files():
    freeze = read_json("baseline_freeze.json")
    changed = []
    for path, digest in freeze["files"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            changed.append(path)
    assert set(changed) <= INTEGRATION_CHANGES, changed
    settings = Settings().model_dump(mode="json", exclude={"neo4j_password"})
    assert {k: settings[k] for k in freeze["settings"]} == freeze["settings"]
    return {
        "frozen_files": len(freeze["files"]),
        "allowed_integration_changes": sorted(changed),
        "protected_files_unchanged": True,
        "baseline_settings_unchanged": True,
    }


def graph_snapshot(db):
    def execute(query, params=None):
        return db.execute(query, params, timeout=30)

    build = execute(
        "MATCH (c:VectorCorpus {id:$id}),(b:VectorBuild {id:c.current_build}) "
        "RETURN properties(b) AS b",
        {"id": Settings().vector_corpus},
    )[0]["b"]
    graph = {
        "nodes": execute(
            "MATCH (n:GraphNode) RETURN properties(n) AS properties, "
            "labels(n) AS labels ORDER BY n.id"
        ),
        "edges": execute(
            "MATCH (a:GraphNode)-[r]->(b:GraphNode) RETURN a.id AS source,b.id AS target,"
            "type(r) AS kind,properties(r) AS properties ORDER BY r.id"
        ),
        "sources": execute(
            "MATCH (s:IngestionSource) RETURN properties(s) AS properties ORDER BY s.id"
        ),
        "runs": execute("MATCH (i:Ingestion) RETURN properties(i) AS properties ORDER BY i.id"),
        "vector_build": build,
        "vectors": execute(
            "MATCH (e:ChunkEmbedding) RETURN properties(e) AS properties ORDER BY e.id"
        ),
    }
    for node in graph["nodes"]:
        node["labels"].sort()
    for kind in ("sources", "runs"):
        for row in graph[kind]:
            for key in ("lock_marker", "claim_token"):
                row["properties"].pop(key, None)
    return graph


def check_graph_snapshot(db):
    snapshot = graph_snapshot(db)
    digest = hashlib.sha256(
        (json.dumps(snapshot, sort_keys=True, indent=2, default=str) + "\n").encode()
    ).hexdigest()
    original = read_json("baseline_freeze.json")["graph_snapshot_sha256"]
    if digest != original:
        (OUT / "snapshot_difference.json").write_text(
            json.dumps(snapshot, indent=2, default=str), encoding="utf-8"
        )
        raise AssertionError(
            "Graph snapshot differs; inspect owned test residue or external changes"
        )
    return {
        "sha256": digest,
        "unchanged": True,
        "counts": {k: len(snapshot[k]) for k in ("nodes", "edges", "sources", "runs", "vectors")},
    }


def runtime_hashes():
    files = [*(ROOT / "app/graph_rag").glob("*.py"), ROOT / "app/api/graph_rag.py"]
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
    }


def check_runtime_freeze():
    freeze = read_json("retrieval_code_freeze.json")
    assert freeze["files"] == runtime_hashes(), "Runtime changed after evaluation freeze"
    return freeze
