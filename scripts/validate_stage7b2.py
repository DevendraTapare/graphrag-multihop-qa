"""Re-run the complete real verification directly against the licensed clean release."""

from scripts.stage7b2_support import OUT, STATE, VENV, run, save
from scripts.validate_stage7b import RESEARCH

COMPOSE = ["docker", "compose", "-p", "graphrag-stage7b2-verification"]


def main():
    python = str(VENV / "Scripts/python.exe")
    rows = []

    def checked(name, args, timeout=1800):
        result = run(name, args, timeout)
        rows.append(result)
        save("validation-progress.json", rows)
        if result["exit_code"]:
            raise RuntimeError(f"Required verification failed: {name}")

    parked = False
    try:
        checked("locked-sync", ["uv", "sync", "--locked"], 900)
        checked("lock-check", ["uv", "lock", "--check"], 120)
        checked("lint", [python, "-m", "ruff", "check", "."], 120)
        checked("format", [python, "-m", "ruff", "format", "--check", "."], 120)
        checked(
            "units",
            [
                python,
                "-m",
                "pytest",
                "tests/unit",
                "-q",
                "-o",
                f"cache_dir={STATE / 'pytest'}",
                f"--junitxml={OUT / 'units.xml'}",
            ],
            300,
        )
        parked = True
        checked("park-research", ["docker", "stop", *RESEARCH], 240)
        checked("start-db", [*COMPOSE, "up", "-d", "--wait", "--wait-timeout", "180"], 240)
        ready = """import time
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
d=GraphDatabaseClient(Settings());end=time.monotonic()+180
while not d.ready() and time.monotonic()<end:time.sleep(1)
if not d.ready():raise RuntimeError('Bolt not ready')
print('Real Neo4j driver ready');d.close()
"""
        checked("bolt-ready", [python, "-c", ready], 210)
        checked(
            "full-tests",
            [
                python,
                "-m",
                "pytest",
                "--run-integration",
                "-q",
                "-o",
                f"cache_dir={STATE / 'pytest'}",
                f"--junitxml={OUT / 'release-tests.xml'}",
            ],
            3000,
        )
        checked(
            "reject-skips",
            [python, "-O", "-m", "scripts.check_ci_results", str(OUT / "release-tests.xml")],
            30,
        )
        for dataset in ("demo", "smoke"):
            checked(
                f"prepare-{dataset}",
                [python, "-m", "scripts.portfolio", "prepare", "--dataset", dataset],
                600,
            )
            checked(
                f"run-{dataset}",
                [
                    python,
                    "-m",
                    "scripts.portfolio",
                    "demo" if dataset == "demo" else "evaluate",
                    "--dataset",
                    dataset,
                    "--output",
                    str(OUT / f"release-{dataset}.json"),
                ],
                600,
            )
    finally:
        if parked:
            rows.append(run("stop-db", [*COMPOSE, "stop"], 120))
            rows.append(run("restore-research", ["docker", "start", *RESEARCH], 120))
        save("validation-results.json", rows)


if __name__ == "__main__":
    main()
