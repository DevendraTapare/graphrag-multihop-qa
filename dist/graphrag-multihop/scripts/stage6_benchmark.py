"""Reproducible Stage 6 entry point; commands never overwrite scored runs or freezes."""

import argparse
import json
from datetime import UTC, datetime

from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from scripts.stage4_support import check_graph_snapshot
from scripts.stage5_support import aligned_snapshot
from scripts.stage6_support import (
    OUT,
    check_freeze,
    check_history,
    digest,
    read,
    runtime_hashes,
    save,
)
from scripts.verify_aligned import snapshot_digest


def historical_databases():
    settings = Settings()
    main = GraphDatabaseClient(settings)
    stage5 = GraphDatabaseClient(
        settings.model_copy(update={"neo4j_uri": settings.stage5_neo4j_uri})
    )
    try:
        old = check_graph_snapshot(main)
        aligned = snapshot_digest(aligned_snapshot(stage5))
        expected = json.loads((OUT.parent / "stage5/provenance_audit.json").read_text())[
            "snapshot_sha256"
        ]
        if not (aligned == expected):
            raise AssertionError("Stage 5 graph changed")
        return {"stage1_to_4": old, "stage5_sha256": aligned}
    finally:
        main.close()
        stage5.close()


def main(command):
    if command == "freeze":
        if not (not (OUT / "configuration_freeze.json").exists()):
            raise AssertionError()
        save(
            "configuration_freeze.json",
            {
                "utc": datetime.now(UTC).isoformat(),
                "files": runtime_hashes(),
                "configuration": {
                    "top_k": 5,
                    "max_hops": 3,
                    "candidate_cap": 128,
                    "max_answers": 10,
                    "seed": 602910,
                    "runtime_tuning": "none; preserve Stage 5 behavior",
                },
            },
        )
        save("historical_databases_before.json", historical_databases())
        print(
            json.dumps(
                {
                    "frozen_files": len(read("configuration_freeze.json")["files"]),
                    "labels_materialized": False,
                }
            )
        )
    elif command == "verify":
        check_freeze()
        before = read("historical_databases_before.json")
        after = historical_databases()
        if not (before == after):
            raise AssertionError()
        save(
            "preservation_verification.json",
            {
                **check_history(),
                "databases": after,
                "runtime_freeze_unchanged": True,
                "uv_lock_sha256": digest((OUT.parent.parent / "uv.lock").read_bytes()),
            },
        )
        print("Historical files, reports, both graph snapshots and frozen runtime verified")
    elif command in {"run1", "run2", "report"}:
        from scripts.evaluate_stage6 import main as evaluate
        from scripts.evaluate_stage6 import report

        report() if command == "report" else evaluate(command)
    elif command in {"load", "profile"}:
        from scripts.performance_stage6 import load, profile

        load() if command == "load" else profile()
    elif command == "recovery":
        from scripts.recovery_stage6 import main as recover

        recover()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["freeze", "verify", "run1", "run2", "report", "load", "profile", "recovery"],
    )
    main(parser.parse_args().command)
