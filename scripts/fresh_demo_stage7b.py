"""Verify the upgraded source-only demo on another initially empty database."""

import json
import math
import os
import secrets
import subprocess
import time

from scripts.stage7b_support import CANDIDATE, OUT, ROOT, STATE, VENV, environment, save
from scripts.validate_stage7b import RESEARCH


def main():
    env = {
        **environment(),
        "NEO4J_URI": "bolt://127.0.0.1:37694",
        "NEO4J_BOLT_PORT": "37694",
        "NEO4J_HTTP_PORT": "37481",
        "NEO4J_PASSWORD": secrets.token_hex(24),
        "PORTFOLIO_STATE_DIR": str(STATE / "fresh-source-demo"),
    }
    (STATE / "fresh-demo-private-environment.json").write_text(json.dumps(env), encoding="utf-8")
    python = str(VENV / "Scripts/python.exe")
    compose = ["docker", "compose", "-p", "graphrag-stage7b-source-demo"]
    rows = []

    def run(name, args, timeout=600):
        print(name, flush=True)
        start = time.monotonic()
        with (OUT / f"fresh-{name}.log").open("w", encoding="utf-8") as log:
            p = subprocess.run(
                args, cwd=CANDIDATE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout
            )
        row = {"step": name, "exit_code": p.returncode, "seconds": time.monotonic() - start}
        rows.append(row)
        save("fresh-demo-progress.json", rows)
        if p.returncode:
            raise ValueError(f"Fresh demo failed: {name}")

    parked = False
    try:
        parked = True
        run("park-research", ["docker", "stop", *RESEARCH], 240)
        run("start", [*compose, "up", "-d", "--wait", "--wait-timeout", "180"], 240)
        before = """import time
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
d=GraphDatabaseClient(Settings())
end=time.monotonic()+180
while not d.ready() and time.monotonic()<end:time.sleep(1)
if not d.ready():raise RuntimeError('Bolt not ready')
n=d.execute('MATCH (n) RETURN count(n) AS n')[0]['n']
if n!=0:raise RuntimeError('Expected initially empty database')
print('Initial node count: 0')
d.close()
"""
        run("verify-empty", [python, "-c", before], 210)
        run("prepare", [python, "-m", "scripts.portfolio", "prepare", "--dataset", "demo"])
        run(
            "responses",
            [python, "-m", "scripts.portfolio", "demo", "--output", str(OUT / "fresh-demo.json")],
        )
        after = """import json
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
d=GraphDatabaseClient(Settings())
r=d.execute("MATCH ()-[r]->() WHERE type(r) IN "
            "['MANAGES','WORKS_FOR','BELONGS_TO','USES','HOSTED_ON'] "
            "RETURN r.extraction_method AS method,count(r) AS facts")
if r!=[{'method':'deterministic_rules','facts':30}]:raise RuntimeError('Unexpected facts')
print(json.dumps({'automatic_facts':30,'manual_facts':0}))
d.close()
"""
        run("verify-facts", [python, "-c", after], 60)
        helper = str(ROOT / "scripts/embedding_sample_stage7b.py")
        old_python = os.path.join(
            "C:/Users/Devendra/.cache/graphrag-stage7a-release-20261029", "Scripts/python.exe"
        )
        for name, executable in (("before", old_python), ("after", python)):
            run(f"embedding-{name}", [executable, helper, str(OUT / f"embedding-{name}.json")], 300)
        old, new = [
            json.loads((OUT / f"embedding-{name}.json").read_bytes())
            for name in ("before", "after")
        ]
        differences = []
        for a, b in zip(old["vectors"], new["vectors"], strict=True):
            cosine = sum(x * y for x, y in zip(a, b, strict=True)) / math.sqrt(
                sum(x * x for x in a) * sum(y * y for y in b)
            )
            differences.append(
                {
                    "dimensions": len(a),
                    "cosine_similarity": cosine,
                    "maximum_absolute_difference": max(
                        abs(x - y) for x, y in zip(a, b, strict=True)
                    ),
                }
            )
        save(
            "embedding-compatibility.json",
            {
                "trusted_cached_model_only": True,
                "samples": differences,
                "embedding_signature_changed": old["embedding_version"] != new["embedding_version"],
                "limit": (
                    "Three fixed text samples; full integration tests cover model, "
                    "index and retrieval behavior."
                ),
            },
        )
    finally:
        if parked:
            try:
                run("stop", [*compose, "stop"], 120)
            finally:
                run("restore-research", ["docker", "start", *RESEARCH], 120)
        save("fresh-demo-results.json", rows)


if __name__ == "__main__":
    main()
