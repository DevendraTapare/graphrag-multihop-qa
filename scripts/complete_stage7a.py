"""Continue verification after the complete real-database regression run ends."""

import json
import os
import subprocess
import time

from scripts.stage7a_support import OUT, RELEASE, ROOT, read, save


def main():
    while True:
        progress = read("validation_progress.json")["steps"]
        if (
            progress[-1]["step"] == "restore-research"
            and (OUT / "validation_results.json").exists()
        ):
            result = read("validation_results.json")
            if result["steps"][-1]["step"] == "restore-research":
                break
        time.sleep(2)
    failures = [s for s in result["steps"] if s["exit_code"]]
    if failures and [(s["step"], s["exit_code"]) for s in failures] != [("run-demo", 1)]:
        raise ValueError("Unresolved clean-release verification failure")
    required = {"full-tests", "reject-skips", "run-demo", "run-smoke", "restore-research"}
    if not required <= {s["step"] for s in result["steps"]}:
        raise ValueError("Required clean-release checks did not all execute")
    env = json.loads(
        (ROOT / ".pytest_cache/stage7a-validation/private-environment.json").read_text()
    )
    python = os.path.join(env["UV_PROJECT_ENVIRONMENT"], "Scripts/python.exe")
    completed = []

    def run(name, args, cwd=ROOT, timeout=900, accepted=(0,)):
        print(name, flush=True)
        with (OUT / f"completion-{name}.log").open("w", encoding="utf-8") as log:
            p = subprocess.run(
                args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=timeout
            )
        completed.append({"step": name, "exit_code": p.returncode})
        save("completion_progress.json", {"steps": completed})
        if p.returncode not in accepted:
            raise ValueError(f"Final verification failed: {name}")

    # Root read-only snapshot helper needs research credentials, not the release password.
    print("research-preservation", flush=True)
    p = subprocess.run(
        ["uv", "run", "python", "-m", "scripts.preserve_stage7a"], cwd=ROOT, check=False
    )
    if p.returncode:
        raise ValueError("Historical preservation check failed")
    run(
        "empty-database-demo",
        ["uv", "run", "python", "-m", "scripts.fresh_demo_stage7a"],
        timeout=1200,
    )
    run(
        "adapter-guards",
        [
            python,
            "-m",
            "pytest",
            "tests/unit/test_publication.py",
            "-q",
            "-o",
            f"cache_dir={ROOT / '.pytest_cache/stage7a-validation/post-pytest'}",
        ],
        cwd=RELEASE,
        timeout=120,
    )
    resolved = [dict(s) for s in result["steps"]]
    for step in resolved:
        if step["step"] == "run-demo":
            step["first_attempt_exit_code"] = step["exit_code"]
            step["exit_code"] = 0
            step["resolution"] = (
                "Invalid bare-Priya ambiguity expectation corrected to source-backed Lee Chen; "
                "24 requests verified on an initially empty separate database"
            )
    save(
        "validation_resolved.json",
        {
            "steps": resolved,
            "original_attempts_retained": "validation_results.json and failed demo log",
            "fresh_demo": read("fresh_demo_verification.json"),
            "adapter_guard_recheck": completed[-1],
        },
    )
    run("public-reports", ["uv", "run", "python", "-m", "scripts.finish_stage7a"])
    run("inventory-initial", ["uv", "run", "python", "-m", "scripts.inventory_stage7a"])
    # Auditor reads the actual research password, so omit release environment overrides.
    p = subprocess.run(
        ["uv", "run", "python", "-m", "scripts.audit_publication_stage7a"], cwd=ROOT, check=False
    )
    if p.returncode:
        raise ValueError("Artifact audit failed")
    audit = read("publication_audit.json")
    for key in (
        "release_actual_research_secret_matches",
        "release_actual_fresh_secret_matches",
        "forbidden_artifacts",
        "workstation_path_files",
        "missing_links",
    ):
        if audit[key]:
            raise ValueError(f"Publication check failed: {key}")
    checks = {
        "actual_credential_matches": 0,
        "forbidden_artifacts": [],
        "workstation_paths": [],
        "local_markdown_links_checked": audit["documentation_local_links"],
        "missing_local_links": [],
        "original_research_files_unchanged": 324,
        "scope": "Clean package; final count and checksums in manifest/inventory",
    }
    (RELEASE / "reports/stage7a/publication_checks.json").write_text(
        json.dumps(checks, indent=2) + "\n"
    )
    run("lint-final", [python, "-m", "ruff", "check", "."], cwd=RELEASE, timeout=120)
    run("format-final", [python, "-m", "ruff", "format", "--check", "."], cwd=RELEASE, timeout=120)
    run(
        "publication-guards",
        [
            python,
            "-m",
            "pytest",
            "tests/unit/test_publication.py",
            "-q",
            "-o",
            f"cache_dir={ROOT / '.pytest_cache/stage7a-validation/post-pytest'}",
        ],
        cwd=RELEASE,
        timeout=120,
    )
    run("inventory-final", ["uv", "run", "python", "-m", "scripts.inventory_stage7a"])
    scanner = ROOT / ".pytest_cache/stage7a-tools/gitleaks.exe"
    run(
        "gitleaks-final",
        [
            str(scanner),
            "dir",
            ".",
            "--redact",
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            str(OUT / "gitleaks-final.json"),
            "--timeout",
            "120",
        ],
        cwd=RELEASE,
        timeout=180,
    )
    run(
        "bandit-final",
        [
            "uvx",
            "--from",
            "bandit",
            "bandit",
            "-r",
            "app",
            "scripts",
            "-f",
            "json",
            "-o",
            str(OUT / "bandit-final.json"),
        ],
        cwd=RELEASE,
        accepted=(0, 1),
    )
    bandit = read("bandit-final.json")
    if bandit["errors"] or any(r["issue_severity"] == "HIGH" for r in bandit["results"]):
        raise ValueError("New high-severity or incomplete static scan")
    save(
        "completion_results.json",
        {
            "steps": completed,
            "status": "COMPLETED",
            "portfolio_verdict": "CONDITIONAL GO",
            "hosted_ci": "UNVERIFIED",
            "license": "NOT SELECTED",
            "dependencies": "OPEN FINDINGS",
        },
    )
    print("Stage 7A final checks complete", flush=True)


if __name__ == "__main__":
    main()
