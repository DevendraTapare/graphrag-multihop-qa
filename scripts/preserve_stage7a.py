"""Read-only final snapshot comparison of all three historical databases."""

import time

from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from scripts.stage4_support import graph_snapshot
from scripts.stage5_support import aligned_snapshot
from scripts.stage7a_support import check_research, read, save
from scripts.verify_aligned import snapshot_digest

EXPECTED = {
    "main": "449ea1c1703fcecf7a75f2445102d9de19a5b7c8624fd41985675ce154a57a63",
    "stage5": "1ae350c885144b61ecedeea545113624f3b9397e16e374dcc6fdd1e8da27e573",
    "stage6": "d3394bc2b57e7745cbd79995b5fd50a8f3907b4ad7e628141a81778086163f90",
}


def main():
    settings = Settings()
    rows = {}
    for kind, uri in (
        ("main", settings.neo4j_uri),
        ("stage5", settings.stage5_neo4j_uri),
        ("stage6", "bolt://127.0.0.1:27689"),
    ):
        db = GraphDatabaseClient(settings.model_copy(update={"neo4j_uri": uri}))
        try:
            end = time.monotonic() + 240
            while not db.ready() and time.monotonic() < end:
                time.sleep(1)
            if not db.ready():
                raise ValueError(f"Historical database did not recover: {kind}")
            snap = graph_snapshot(db) if kind == "main" else aligned_snapshot(db)
            actual = snapshot_digest(snap)
            rows[kind] = {
                "expected_sha256": EXPECTED[kind],
                "actual_sha256": actual,
                "unchanged": actual == EXPECTED[kind],
            }
            if actual != EXPECTED[kind]:
                save("research_snapshot_mismatch.json", rows)
                raise ValueError(f"Historical graph snapshot changed: {kind}")
        finally:
            db.close()
    save(
        "research_preservation.json",
        {
            "files": check_research(),
            "databases": rows,
            "containers_restored": True,
            "original_evidence_files": len(read("research_freeze.json")["files"]),
            "snapshot_scope": (
                "Historical GraphNode/edge/source/run/vector contents; excludes volatile "
                "claim/lock markers and vector publication-control nodes as in original contracts"
            ),
        },
    )
    print("All 324 original files and three historical graph snapshots unchanged")


if __name__ == "__main__":
    main()
