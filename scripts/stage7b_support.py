"""Security candidate orchestration; private state stays outside the publication."""

import hashlib
import json
import os
import secrets
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/stage7b"
CANDIDATE = ROOT / ".pytest_cache/stage7b-candidate"
STATE = ROOT / ".pytest_cache/stage7b-validation"
VENV = Path("C:/Users/Devendra/.cache/graphrag-stage7b-security-20261029")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def environment():
    STATE.mkdir(exist_ok=True)
    private = STATE / "private-environment.json"
    if private.exists():
        return json.loads(private.read_text())
    env = {
        **os.environ,
        "UV_PROJECT_ENVIRONMENT": str(VENV),
        "PYTHONPYCACHEPREFIX": str(STATE / "bytecode"),
        "RUFF_CACHE_DIR": str(STATE / "ruff"),
        "PORTFOLIO_STATE_DIR": str(STATE / "portfolio-state"),
        "APP_ENV": "development",
        "NEO4J_URI": "bolt://127.0.0.1:37693",
        "NEO4J_HTTP_PORT": "37480",
        "NEO4J_BOLT_PORT": "37693",
        "NEO4J_POOL_SIZE": "50",
        "NEO4J_PASSWORD": secrets.token_hex(24),
        "PYTHONUNBUFFERED": "1",
    }
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    private.write_text(json.dumps(env), encoding="utf-8")
    return env


def run(name, args, timeout=1800, cwd=CANDIDATE):
    print(name, flush=True)
    start = time.monotonic()
    with (OUT / f"{name}.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(
            args, cwd=cwd, env=environment(), stdout=log, stderr=subprocess.STDOUT, timeout=timeout
        )
    row = {"step": name, "exit_code": result.returncode, "seconds": time.monotonic() - start}
    save(f"{name}-result.json", row)
    print(json.dumps(row), flush=True)
    return row


def refresh_overrides():
    path = CANDIDATE / "PUBLICATION.json"
    manifest = json.loads(path.read_text())
    before = json.loads((OUT / "stage7a_release_freeze.json").read_text())["files"]
    security = {}
    for relative, old in before.items():
        if relative in {"PUBLICATION.json", "FILE_INVENTORY.json", "SHA256SUMS"}:
            continue
        now = digest(CANDIDATE / relative)
        if now == old:
            continue
        if relative in {"pyproject.toml", "uv.lock"}:
            reason = (
                "Stage 7B: verified Transformers 5.17 dependency migration "
                "and hardened XML dev parser"
            )
        elif relative.startswith("scripts/"):
            reason = (
                "Stage 7B: explicit verification/preservation exceptions under -O; "
                "defusedxml for JUnit readers"
            )
        elif relative == "tests/unit/test_graph_rag.py":
            reason = (
                "Stage 7B: exact named security-file allowlist; "
                "retain original/release hash and core checks"
            )
        else:
            reason = (
                "Stage 7B: current security results, release metadata "
                "and historical-context clarification"
            )
        security[relative] = {"stage7a_sha256": old, "release_sha256": now, "reason": reason}
        if (ROOT / relative).exists():
            manifest["overrides"][relative] = {
                "source_sha256": digest(ROOT / relative),
                "release_sha256": now,
                "reason": reason,
            }
    manifest["security_overrides"] = security
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    refresh_overrides()
    run("environment-sync", ["uv", "sync", "--locked"], 1200)
