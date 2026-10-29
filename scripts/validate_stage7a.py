"""Execute the clean release in a new environment, preserving research containers."""

import json
import os
import secrets
import subprocess
import time
from pathlib import Path

from scripts.stage7a_support import OUT, RELEASE, ROOT, check_research, save

RESEARCH = (
    "graphrag-multihop-neo4j-1",
    "graphrag-stage5-neo4j-1",
    "graphrag-stage6-neo4j-1",
)


def main():
    check_research()
    cache = ROOT / ".pytest_cache/stage7a-validation"
    cache.mkdir(parents=True, exist_ok=True)
    venv = Path(os.environ.get("STAGE7A_VENV", str(cache / "venv")))
    env = {
        **os.environ,
        "UV_PROJECT_ENVIRONMENT": str(venv),
        "PYTHONDONTWRITEBYTECODE": "1",
        "RUFF_CACHE_DIR": str(cache / "ruff"),
        "PORTFOLIO_STATE_DIR": str(cache / "portfolio-state"),
        "APP_ENV": "development",
        "NEO4J_URI": "bolt://127.0.0.1:37690",
        "NEO4J_HTTP_PORT": "37477",
        "NEO4J_BOLT_PORT": "37690",
        "NEO4J_POOL_SIZE": "50",
        "NEO4J_PASSWORD": secrets.token_hex(24),
    }
    # Private recovery material is outside the publication and never printed.
    (cache / "private-environment.json").write_text(json.dumps(env), encoding="utf-8")
    python = str(venv / "Scripts/python.exe")
    steps = []

    def run(name, args, timeout=1800):
        print(name, flush=True)
        started = time.monotonic()
        with (OUT / f"validation-{name}.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                args, cwd=RELEASE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout
            )
        steps.append(
            {"step": name, "exit_code": result.returncode, "seconds": time.monotonic() - started}
        )
        save("validation_progress.json", {"steps": steps})
        return result.returncode == 0

    parked = False
    try:
        if not run("fresh-environment", ["uv", "sync", "--locked"], 900):
            raise ValueError("Fresh environment installation failed; inspect private log")
        run("park-research", ["docker", "stop", *RESEARCH], 240)
        parked = True
        if not run(
            "start-release-db",
            ["docker", "compose", "up", "-d", "--wait", "--wait-timeout", "180"],
            240,
        ):
            raise ValueError("Fresh publication database startup failed")
        # TCP health is not Bolt readiness; use the actual driver within its normal bounds.
        ready_code = """import time
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
d=GraphDatabaseClient(Settings())
end=time.monotonic()+180
while not d.ready() and time.monotonic()<end: time.sleep(1)
assert d.ready(), 'Bolt did not become ready'
d.close()
"""
        if not run("bolt-ready", [python, "-c", ready_code], 210):
            raise ValueError("Bolt readiness failed")
        run("lint", [python, "-m", "ruff", "check", "."], 120)
        run("format", [python, "-m", "ruff", "format", "--check", "."], 120)
        run(
            "full-tests",
            [
                python,
                "-m",
                "pytest",
                "--run-integration",
                "-q",
                "-o",
                f"cache_dir={cache / 'pytest'}",
                f"--junitxml={OUT / 'release-tests.xml'}",
            ],
            2400,
        )
        run(
            "reject-skips",
            [python, "-m", "scripts.check_ci_results", str(OUT / "release-tests.xml")],
            30,
        )
        for kind in ("demo", "smoke"):
            if run(
                f"prepare-{kind}",
                [python, "-m", "scripts.portfolio", "prepare", "--dataset", kind],
                600,
            ):
                args = [
                    python,
                    "-m",
                    "scripts.portfolio",
                    "demo" if kind == "demo" else "evaluate",
                    "--dataset",
                    kind,
                    "--output",
                    str(OUT / f"release-{kind}.json"),
                ]
                run(f"run-{kind}", args, 600)
    finally:
        if parked:
            run("stop-release-db", ["docker", "compose", "stop"], 120)
            run("restore-research", ["docker", "start", *RESEARCH], 120)
        save(
            "validation_results.json",
            {
                "steps": steps,
                "research_files": check_research(),
                "environment": (
                    "New virtual environment and new dedicated Neo4j volume; "
                    "existing cached image/model/packages reused"
                ),
            },
        )
    print("Clean verification steps finished; inspect recorded exit codes", flush=True)


if __name__ == "__main__":
    main()
