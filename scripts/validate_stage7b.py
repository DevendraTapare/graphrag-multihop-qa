"""Run real regressions with isolated release data, restoring research services."""

from scripts.stage7b_support import OUT, STATE, VENV, refresh_overrides, run, save

RESEARCH = (
    "graphrag-multihop-neo4j-1",
    "graphrag-stage5-neo4j-1",
    "graphrag-stage6-neo4j-1",
)
COMPOSE = ["docker", "compose", "-p", "graphrag-stage7b-security"]


def main():
    refresh_overrides()
    python = str(VENV / "Scripts/python.exe")
    steps = []

    def checked(name, args, timeout=1800):
        result = run(name, args, timeout)
        steps.append(result)
        save("validation-progress.json", steps)
        if result["exit_code"]:
            raise RuntimeError(f"Required step failed: {name}")

    parked = False
    try:
        checked("lint", [python, "-m", "ruff", "check", "."], 120)
        checked("format", [python, "-m", "ruff", "format", "--check", "."], 120)
        checked("lock-check", ["uv", "lock", "--check"], 120)
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
            240,
        )
        checked("park-research", ["docker", "stop", *RESEARCH], 240)
        parked = True
        checked("start-db", [*COMPOSE, "up", "-d", "--wait", "--wait-timeout", "180"], 240)
        ready = """import time
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
d=GraphDatabaseClient(Settings())
end=time.monotonic()+180
while not d.ready() and time.monotonic()<end:time.sleep(1)
if not d.ready():raise RuntimeError('Bolt not ready')
print({'initial_nodes':d.execute('MATCH (n) RETURN count(n) AS n')[0]['n']})
d.close()
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
            steps.append(run("stop-db", [*COMPOSE, "stop"], 120))
            steps.append(run("restore-research", ["docker", "start", *RESEARCH], 120))
        save("validation-results.json", steps)


if __name__ == "__main__":
    main()
