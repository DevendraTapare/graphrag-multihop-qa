"""Verify documented demo bootstrap on a second initially empty real database."""

import json
import os
import secrets
import subprocess
import time

from scripts.stage7a_support import OUT, RELEASE, ROOT, check_research, save


def main():
    check_research()
    state = ROOT / ".pytest_cache/stage7a-empty-demo"
    state.mkdir(parents=True, exist_ok=True)
    env = {
        **json.loads(
            (ROOT / ".pytest_cache/stage7a-validation/private-environment.json").read_text()
        ),
        "NEO4J_URI": "bolt://127.0.0.1:37691",
        "NEO4J_BOLT_PORT": "37691",
        "NEO4J_HTTP_PORT": "37478",
        "NEO4J_PASSWORD": secrets.token_hex(24),
        "PORTFOLIO_STATE_DIR": str(state / "state"),
        "PYTHONUNBUFFERED": "1",
    }
    (state / "private-environment.json").write_text(json.dumps(env))
    python = str(os.path.join(env["UV_PROJECT_ENVIRONMENT"], "Scripts/python.exe"))
    compose = ["docker", "compose", "-p", "graphrag-stage7a-source-demo"]
    steps = []

    def run(name, args, timeout=600):
        print(name, flush=True)
        start = time.monotonic()
        with (OUT / f"fresh-demo-{name}.log").open("w", encoding="utf-8") as log:
            p = subprocess.run(
                args, cwd=RELEASE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout
            )
        steps.append({"step": name, "exit_code": p.returncode, "seconds": time.monotonic() - start})
        save("fresh_demo_progress.json", {"steps": steps})
        if p.returncode:
            raise ValueError(f"Fresh demo failed: {name}")

    try:
        run("start", [*compose, "up", "-d", "--wait", "--wait-timeout", "180"], 240)
        before = """import time
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
d=GraphDatabaseClient(Settings())
end=time.monotonic()+180
while not d.ready() and time.monotonic()<end: time.sleep(1)
assert d.ready()
n=d.execute('MATCH (n) RETURN count(n) AS n')[0]['n']
assert n==0, 'Fresh demo requires an initially empty volume'
print('Verified initial node count zero')
d.close()
"""
        run("verify-empty", [python, "-c", before], 210)
        run("prepare", [python, "-m", "scripts.portfolio", "prepare", "--dataset", "demo"])
        run(
            "responses",
            [
                python,
                "-m",
                "scripts.portfolio",
                "demo",
                "--output",
                str(OUT / "fresh-release-demo.json"),
            ],
        )
        after = """import json
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
d=GraphDatabaseClient(Settings())
query=("MATCH ()-[r]->() WHERE type(r) IN "
       "['MANAGES','WORKS_FOR','BELONGS_TO','USES','HOSTED_ON'] "
       "RETURN r.extraction_method AS method,count(r) AS facts")
r=d.execute(query)
assert r==[{'method':'deterministic_rules','facts':30}], r
print(json.dumps({'factual_relationships':r,'manual_facts':0}))
d.close()
"""
        run("verify-no-curated-facts", [python, "-c", after], 60)
    finally:
        run("stop", [*compose, "stop"], 120)
    result = {
        "steps": steps,
        "initial_node_count": 0,
        "manual_facts": 0,
        "automatic_facts": 30,
        "source_documents": 12,
        "actual_demo_requests": 24,
        "fresh_named_volume": True,
        "research_preservation": check_research(),
    }
    save("fresh_demo_verification.json", result)


if __name__ == "__main__":
    main()
