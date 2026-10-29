"""Final license verification helpers; private tooling is outside the release."""

import hashlib
import json
import os
import secrets
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "dist/graphrag-multihop"
OUT = ROOT / "reports/stage7b2"
STATE = ROOT / ".pytest_cache/stage7b2-validation"
VENV = Path("C:/Users/Devendra/.cache/graphrag-stage7b-security-20261029")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(name):
    return json.loads((OUT / name).read_bytes())


def save(name, value):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def environment():
    STATE.mkdir(exist_ok=True)
    private = STATE / "private-environment.json"
    if private.exists():
        return json.loads(private.read_bytes())
    env = {
        **os.environ,
        "UV_PROJECT_ENVIRONMENT": str(VENV),
        "PYTHONPYCACHEPREFIX": str(ROOT / ".pytest_cache/stage7b-validation/bytecode"),
        "RUFF_CACHE_DIR": str(STATE / "ruff"),
        "PORTFOLIO_STATE_DIR": str(STATE / "portfolio-state"),
        "APP_ENV": "development",
        "NEO4J_URI": "bolt://127.0.0.1:37695",
        "NEO4J_HTTP_PORT": "37482",
        "NEO4J_BOLT_PORT": "37695",
        "NEO4J_POOL_SIZE": "50",
        "NEO4J_PASSWORD": secrets.token_hex(24),
        "PYTHONUNBUFFERED": "1",
    }
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    private.write_text(json.dumps(env), encoding="utf-8")
    return env


def run(name, args, timeout=1800):
    print(name, flush=True)
    start = time.monotonic()
    with (OUT / f"{name}.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(
            args,
            cwd=RELEASE,
            env=environment(),
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    row = {"step": name, "exit_code": result.returncode, "seconds": time.monotonic() - start}
    save(f"{name}-result.json", row)
    print(json.dumps(row), flush=True)
    return row


def update_publication():
    path = RELEASE / "PUBLICATION.json"
    manifest = json.loads(path.read_bytes())
    before = read("stage7b_release_freeze.json")["files"]
    changes = {}
    for relative, old in before.items():
        if relative in {"PUBLICATION.json", "FILE_INVENTORY.json", "SHA256SUMS"}:
            continue
        now = digest(RELEASE / relative)
        if old == now:
            continue
        reason = (
            "Stage 7B.2: approved MIT scope, third-party notices or final release documentation"
        )
        changes[relative] = {"stage7b_sha256": old, "release_sha256": now, "reason": reason}
        if relative in manifest["overrides"]:
            manifest["overrides"][relative].update(release_sha256=now, reason=reason)
    manifest.update(
        stage="7B.2",
        license_selected=True,
        license="MIT",
        copyright_holder="Devendra Tapare",
        copyright_year=2026,
        license_scope=(
            "First-party code and original material the owner owns or may license; "
            "third-party terms remain separate"
        ),
        security_overrides_scope=(
            "Historical Stage 7B.1 snapshot; current documentation differences "
            "are in license_overrides"
        ),
        license_overrides=changes,
        precommit_review="docs/STAGE7B_PRECOMMIT_REPORT.md",
        previous_release="reports/stage7b2/previous-release.json",
        change_record="reports/stage7b2/release-changes.json",
    )
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
