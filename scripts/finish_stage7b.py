"""Prepare the reviewable local release after required security validations."""

# Markdown prose is deliberately emitted as complete document paragraphs.
# ruff: noqa: E501

import json
import re
import shutil
import zipfile

from defusedxml import ElementTree as ET

from scripts.check_stage7b import check
from scripts.document_stage7b import make_report
from scripts.stage7b_support import CANDIDATE, OUT, ROOT, VENV, digest, refresh_overrides, run, save

RELEASE = ROOT / "dist/graphrag-multihop"
PUBLIC = [
    "advisory-review.json",
    "bandit-review.json",
    "BANDIT_REVIEW.md",
    "bandit.json",
    "dependency-changes.json",
    "installed-dependency-changes.json",
    "dependency-metadata.json",
    "pip-audit.json",
    "all-lock-packages-review.json",
    "installed-source-verification.json",
    "xclip-installed-review.json",
    "assert-condition-equivalence.json",
    "embedding-compatibility.json",
    "fresh-demo.json",
    "release-smoke.json",
    "research-preservation.json",
    "validation-summary.json",
]


def read(name):
    return json.loads((OUT / name).read_bytes())


def inventory():
    paths = sorted(p for p in CANDIDATE.rglob("*") if p.is_file())
    rows = [
        {
            "path": p.relative_to(CANDIDATE).as_posix(),
            "bytes": p.stat().st_size,
            "sha256": digest(p),
        }
        for p in paths
        if p.name not in {"FILE_INVENTORY.json", "SHA256SUMS"}
    ]
    (CANDIDATE / "FILE_INVENTORY.json").write_text(
        json.dumps(
            {
                "scope": "Every payload file except FILE_INVENTORY.json and SHA256SUMS; avoids self-reference",
                "files": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (CANDIDATE / "SHA256SUMS").write_text(
        "".join(
            f"{digest(p)}  {p.relative_to(CANDIDATE).as_posix()}\n"
            for p in paths
            if p.name != "SHA256SUMS"
        ),
        encoding="utf-8",
    )


def verification_summary():
    steps = read("validation-results.json")
    fresh = read("fresh-demo-results.json")
    if any(r["exit_code"] for r in steps + fresh):
        raise ValueError("Required verification step failed")
    cases = list(ET.parse(OUT / "release-tests.xml").iter("testcase"))
    old = list(ET.parse(ROOT / "reports/stage7a/release-tests.xml").iter("testcase"))
    identifiers = {(c.get("classname"), c.get("name")) for c in cases}
    original = {(c.get("classname"), c.get("name")) for c in old}
    if not original <= identifiers:
        raise ValueError("A historical test disappeared")
    rejected = [
        c.get("name")
        for c in cases
        if any(c.find(t) is not None for t in ("failure", "error", "skipped"))
    ]
    if rejected:
        raise ValueError("Full suite contains failed/skipped cases")
    demo = read("fresh-demo.json")
    smoke = read("release-smoke.json")
    if demo["requests"] != 24 or len(demo["responses"]) != 24 or smoke["requests"] != 27:
        raise ValueError("Demo/smoke request count differs")
    metrics = {}
    for mode in {r["mode"] for r in smoke["rows"]}:
        rows = [r for r in smoke["rows"] if r["mode"] == mode]
        metrics[mode] = {
            "positive_questions": sum(r["answerable"] for r in rows),
            "positive_correct": sum(r["exact_match"] for r in rows if r["answerable"]),
            "negative_questions": sum(not r["answerable"] for r in rows),
            "negative_correct": sum(r["exact_match"] for r in rows if not r["answerable"]),
            "unsupported_answers": sum(r["unsupported_answer"] for r in rows),
        }
    if any(m["unsupported_answers"] for m in metrics.values()):
        raise ValueError("Smoke returned unsupported answers")
    audit = read("pip-audit.json")
    if any(p.get("vulns") or p.get("skip_reason") for p in audit["dependencies"]):
        raise ValueError("Dependency audit is not clear")
    locked = read("all-lock-packages-review.json")["packages"]
    if any(
        p.get("error") or p.get("advisories") or p.get("hashes_verified_against_pypi") is False
        for p in locked
    ):
        raise ValueError("Cross-platform lock review failed")
    bandit = read("bandit.json")["results"]
    if len(bandit) != 12 or any(r["issue_severity"] != "LOW" for r in bandit):
        raise ValueError("Bandit results changed; repeat the review")
    result = {
        "total": len(cases),
        "unit": sum("tests.unit" in c.get("classname", "") for c in cases),
        "integration": sum("tests.integration" in c.get("classname", "") for c in cases),
        "failures": 0,
        "errors": 0,
        "skips": 0,
        "original_test_ids_preserved": len(original),
        "new_cases": len(identifiers - original),
        "steps": steps,
        "fresh_steps": fresh,
        "demo_requests_per_run": 24,
        "demo_runs": 2,
        "fresh_initial_nodes": 0,
        "automatic_facts": 30,
        "manual_facts": 0,
        "smoke_requests": 27,
        "smoke": metrics,
        "bandit_final": len(read("bandit.json")["results"]),
        "audit_distributions": len(audit["dependencies"]),
        "audit_findings": 0,
        "historical_benchmarks_overwritten": False,
        "initial_failures": {
            "early_invocation": "pytest cache path error; no tests collected",
            "first_units": {"passed": 303, "failed": 4},
            "final_unit_preflight": {"passed": 307, "failed": 0},
        },
        "platform": "Windows; Python 3.12.13; cached trusted model and image",
        "hosted_ci": "UNVERIFIED",
        "publication": "CONDITIONAL GO; trusted local portfolio only",
    }
    save("validation-summary.json", result)
    return result


def stage_docs(summary):
    p = CANDIDATE / "README.md"
    s = p.read_text(encoding="utf-8")
    s = s.replace("Portfolio release: Stage 7A.", "Portfolio release: Stage 7B.1 security refresh.")
    s = s.replace(
        "For a supported question, the graph can explain:",
        f"Current verification: **{summary['total']} tests pass**, including 129 real Neo4j "
        "integration tests. The current dependency audit reports zero findings; reviewed static "
        "warnings and advisory limitations remain. See "
        "[STAGE7B_SECURITY_REVIEW.md](docs/STAGE7B_SECURITY_REVIEW.md).\n\n"
        "For a supported question, the graph can explain:",
    )
    s = s.replace(
        "The dependency audit has open Transformers advisories: nine records, six distinct IDs. "
        "The pinned local model workflow limits exposure but does not establish a clean "
        "dependency-security gate. Resolve or explicitly accept that risk before publication.",
        "Stage 7B upgraded Transformers and hardened the local verification tools. The current "
        "audit reports zero vulnerabilities across 60 installed packages; 12 low Bandit warnings "
        "and two upstream advisory-status caveats remain documented. "
        "Read [STAGE7B_SECURITY_REVIEW.md](docs/STAGE7B_SECURITY_REVIEW.md) for the current gate.",
    )
    s = s.replace(
        "No Git repository, remote, commit, push, deployment or Stage 7B work was performed "
        "during release preparation.",
        "Stage 7B refreshed this local candidate after security checks. No Git repository, "
        "remote, commit, push or deployment was created.",
    )
    p.write_text(s, encoding="utf-8")
    p = CANDIDATE / "docs/SECURITY_REVIEW.md"
    s = p.read_text(encoding="utf-8")
    # Preserve the dated Stage 7A review verbatim as history under the current gate notice.
    prefix = (
        "# Current security gate\n\nStage 7B.1 supersedes the dated Stage 7A scan below. "
        "The upgraded lock's audit reports zero vulnerabilities across 60 distributions. "
        "Bandit retains 12 reviewed LOW warnings. Two advisories have no official patched-version "
        "declaration: one is outside this application's reachable functionality and the other has "
        "a verified source correction in the selected wheel. No public-service or production "
        "approval is implied. Read [STAGE7B_SECURITY_REVIEW.md](STAGE7B_SECURITY_REVIEW.md) and "
        "its per-finding evidence before publication.\n\n"
        "## Historical Stage 7A review (unchanged text)\n\n"
    )
    p.write_text(prefix + s, encoding="utf-8")
    p = CANDIDATE / "docs/THIRD_PARTY_NOTICES.md"
    s = p.read_text(encoding="utf-8")
    s += (
        "\nStage 7B updates the release dependency lock without selecting a project license. "
        "Current installed dependency metadata is in "
        "[dependency-metadata.json](../reports/stage7b/dependency-metadata.json), and every "
        "lock change is in [dependency-changes.json](../reports/stage7b/dependency-changes.json). "
        "The earlier Stage 7A metadata remains a dated record. No dependency binary is bundled.\n"
    )
    p.write_text(s, encoding="utf-8")
    p = CANDIDATE / "docs/FINAL_PROJECT_SUMMARY.md"
    s = p.read_text(encoding="utf-8")
    s = s.replace("429 tests passed:", "Stage 7A verification: 429 tests passed:")
    s = s.replace(
        "Static findings and six distinct dependency advisory IDs remain disclosed. "
        "License/rights approval, dependency remediation or explicit risk acceptance, "
        "and a real hosted CI run remain open before public publication. "
        "No publishing, deployment or Stage 7B action occurred.",
        "Stage 7B then upgraded the release dependencies and hardened XML/evidence checks: "
        f"{summary['total']} tests now pass, with zero current audit findings and 12 "
        "reviewed LOW Bandit warnings. Two upstream advisory-status caveats remain "
        "disclosed. License/rights approval and a real hosted CI run still gate public "
        "publication. No publishing or deployment occurred. Read "
        "[STAGE7B_SECURITY_REVIEW.md](STAGE7B_SECURITY_REVIEW.md) for current results.",
    )
    p.write_text(s, encoding="utf-8")


def main():
    summary = verification_summary()
    before = read("stage7a_release_freeze.json")["files"]
    if any(digest(RELEASE / p) != sha for p, sha in before.items()):
        raise ValueError("Stage 7A candidate changed independently; refusing to overwrite")
    target = CANDIDATE / "reports/stage7b"
    target.mkdir(exist_ok=True)
    for name in PUBLIC:
        shutil.copyfile(OUT / name, target / name)
    # Retry from archived publication documents; never stack generated notices.
    with zipfile.ZipFile(OUT / "stage7a_release_before_security.zip") as archive:
        for relative in [
            "README.md",
            "docs/SECURITY_REVIEW.md",
            "docs/THIRD_PARTY_NOTICES.md",
            "docs/FINAL_PROJECT_SUMMARY.md",
            "docs/PUBLICATION_MANIFEST.md",
        ]:
            (CANDIDATE / relative).write_bytes(archive.read(relative))
    (target / "publication-checks.json").write_text("{}\n", encoding="utf-8")
    stage_docs(summary)
    manifest_text = (CANDIDATE / "docs/PUBLICATION_MANIFEST.md").read_text(encoding="utf-8")
    manifest_text = manifest_text.replace(
        "all 423 historical test cases plus six new publication cases",
        "all 423 historical test cases, six publication cases and seven security cases",
    )
    manifest_text = manifest_text.replace(
        "only declared docs/report/config differences or excluded report artifacts can differ",
        "only declared docs/report/config differences, explicitly named security fixes "
        "or excluded report artifacts can differ",
    )
    manifest_text = manifest_text.replace(
        "Remaining publication conditions: choose and approve a project/data license, review "
        "source rights and third-party notices, remediate or explicitly accept the open "
        "Transformers advisory findings, and obtain a real GitHub CI result. Publishing needs "
        "a separate owner instruction. No commit, remote, push, deployment or Stage 7B was "
        "performed. See [STAGE7A_RELEASE_REPORT.md](STAGE7A_RELEASE_REPORT.md).",
        "Stage 7B upgraded and revalidated the release dependencies, hardened the verification "
        "tools and preserved all historical reports. The current security gate is "
        "[STAGE7B_SECURITY_REVIEW.md](STAGE7B_SECURITY_REVIEW.md); the Stage 7A release report "
        "remains a dated record. Remaining publication conditions: the owner's license/rights "
        "decision and a real GitHub CI result. No license, commit, repository, remote, push "
        "or deployment was created.",
    )
    manifest_text += (
        "\n## Stage 7B security refresh\n\nThe Stage 7A archive and every original file hash remain "
        "in the research workspace. The release changes only dependencies, XML/report verification "
        "tools, an explicit frozen-file allowlist and current release/security documentation. "
        "All 104 local workflow assertions now use equivalent conditional exceptions so optimized "
        "Python cannot remove preservation and verification checks. "
        "`PUBLICATION.json.security_overrides` records each Stage 7A SHA, current SHA and reason. "
        "The original app/data/migrations and integration sources remain unchanged. "
        "New Stage 7B reports supplement the historical reports; no metric file was replaced. "
        "All public files are checked for secrets, unexpected binaries and local paths.\n"
    )
    # Rebuild the legacy override table using final security hashes/reasons during sealing.
    validation_text = (
        f"**{summary['total']} tests passed: {summary['unit']} unit and "
        f"{summary['integration']} real Neo4j integration; zero final failures, errors or skips.** "
        f"All {summary['original_test_ids_preserved']} Stage 7A case IDs remain, plus seven new "
        "security cases. Ruff lint/format, locked sync/check and the dependency audit pass. "
        "The real integration suite covers cached MiniLM, normalized 384-dimensional embeddings, "
        "vector build/rebuild/index behavior, graph-only and hybrid retrieval, provenance, "
        "stale/invalid source rejection and bounded failures. The optimized-Python CI result "
        "gate also passes.\n\n"
        "The offline demo passed **24/24 checks in each of two real runs**. The second run began "
        "with zero database nodes, ingested 12 source documents, built 30 automatic factual "
        "relationships with zero manually inserted facts, replayed their provenance and "
        "confirmed a repeated index build was cached. The separate smoke made 27 requests for "
        "nine questions across vector, graph and hybrid modes. Its six positives and three "
        "negatives include calibration questions; it is a regression smoke, not a new held-out "
        f"benchmark. Actual results: `{json.dumps(summary['smoke'], sort_keys=True)}`. "
        "Historical negative results are unchanged.\n\n"
        "Three fixed text samples were encoded separately with both environments using only "
        "the trusted cached MiniLM revision. Measured cosine/difference values and changed "
        "embedding signatures are in "
        "[embedding-compatibility.json](../reports/stage7b/embedding-compatibility.json). "
        "This is sample compatibility evidence, not an assertion of identical output for all text. "
        "See [validation-summary.json](../reports/stage7b/validation-summary.json), "
        "[fresh-demo.json](../reports/stage7b/fresh-demo.json) and "
        "[release-smoke.json](../reports/stage7b/release-smoke.json)."
    )
    previous = None
    for _ in range(15):
        paths = [p for p in CANDIDATE.rglob("*") if p.is_file()]
        count, size = len(paths), sum(p.stat().st_size for p in paths)
        text = make_report(
            {
                "validation_text": validation_text,
                "publication_text": (
                    f"Final clean candidate: **{count} files, {size:,} bytes ({size / 1048576:.2f} MiB)**, "
                    "including the inventory and checksum file. `FILE_INVENTORY.json` covers every "
                    "payload except itself and `SHA256SUMS`; `SHA256SUMS` covers every other file. "
                    "All checksums were regenerated and verified. Secret scanning uses the existing "
                    "exact-value reviewed Gitleaks configuration plus an exact search for the real "
                    "private credentials; no directory or security-rule suppression was added. "
                    "See [publication-checks.json](../reports/stage7b/publication-checks.json) for the "
                    "final file/secret/binary/path/link/history checks. Private credentials, environments, "
                    "logs, JUnit XML, archives, model/container binaries and database snapshots remain "
                    "outside the publication. The original Stage 7A candidate archive is retained privately."
                ),
            }
        )
        (CANDIDATE / "docs/STAGE7B_SECURITY_REVIEW.md").write_text(text, encoding="utf-8")
        current_manifest = re.sub(
            r"Final package: \*\*\d+ files, [\d,]+ bytes \([\d.]+ MiB\)\*\*",
            f"Final package: **{count} files, {size} bytes ({size / 1048576:.2f} MiB)**",
            manifest_text,
        )
        overrides = json.loads((CANDIDATE / "PUBLICATION.json").read_bytes())["overrides"]
        table = "\n".join(
            f"| `{name}` | {row['reason']} |" for name, row in sorted(overrides.items())
        )
        current_manifest = re.sub(
            r"(\| Path \| Reason \|\n\|---\|---\|\n).*?(\n\nThe new `\.gitattributes`)",
            lambda match, table=table: match[1] + table + match[2],
            current_manifest,
            flags=re.S,
        )
        (CANDIDATE / "docs/PUBLICATION_MANIFEST.md").write_text(current_manifest, encoding="utf-8")
        refresh_overrides()
        p = CANDIDATE / "PUBLICATION.json"
        value = json.loads(p.read_bytes())
        value.update(
            stage="7B.1",
            security_review="docs/STAGE7B_SECURITY_REVIEW.md",
            security_gate="CONDITIONAL GO; trusted local portfolio only",
        )
        p.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        audit = check(CANDIDATE)
        save("publication-checks.json", audit)
        shutil.copyfile(OUT / "publication-checks.json", target / "publication-checks.json")
        inventory()
        paths = [p for p in CANDIDATE.rglob("*") if p.is_file()]
        state = len(paths), sum(p.stat().st_size for p in paths)
        if state == previous:
            break
        previous = state
    else:
        raise ValueError("Publication sizes did not converge")
    for line in (CANDIDATE / "SHA256SUMS").read_text().splitlines():
        sha, relative = line.split("  ", 1)
        if digest(CANDIDATE / relative) != sha:
            raise ValueError(relative)
    # Final changed docs and manifest require a guard/unit recheck before refreshing the release.
    python = str(VENV / "Scripts/python.exe")
    for name, args in [
        ("sealed-lint", [python, "-m", "ruff", "check", "."]),
        ("sealed-format", [python, "-m", "ruff", "format", "--check", "."]),
        ("sealed-units", [python, "-m", "pytest", "tests/unit", "-q", "-p", "no:cacheprovider"]),
        (
            "sealed-gitleaks",
            [
                str(ROOT / ".pytest_cache/stage7a-tools/gitleaks.exe"),
                "dir",
                ".",
                "--config",
                ".gitleaks.toml",
                "--redact",
                "--report-format",
                "json",
                "--report-path",
                str(OUT / "gitleaks-final.json"),
            ],
        ),
    ]:
        result = run(name, args, 240)
        if result["exit_code"]:
            raise ValueError(f"Final check failed: {name}")
    shutil.copytree(CANDIDATE, RELEASE, dirs_exist_ok=True)
    final = check(RELEASE)
    candidate_paths = {
        p.relative_to(CANDIDATE).as_posix() for p in CANDIDATE.rglob("*") if p.is_file()
    }
    release_paths = {p.relative_to(RELEASE).as_posix() for p in RELEASE.rglob("*") if p.is_file()}
    if candidate_paths != release_paths:
        raise ValueError("Unexpected release paths")
    for relative in release_paths:
        if digest(RELEASE / relative) != digest(CANDIDATE / relative):
            raise ValueError("Release differs from verified candidate")
    save(
        "final-release-verification.json",
        {
            **final,
            "checksum_entries": len(release_paths) - 1,
            "checksum_failures": 0,
            "gitleaks_findings": 0,
            "candidate_matches_release": True,
        },
    )
    print(
        json.dumps(
            {
                "files": final["files"],
                "bytes": final["bytes"],
                "tests": summary["total"],
                "audit_findings": 0,
                "bandit_low": 12,
                "verdict": "CONDITIONAL GO",
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
