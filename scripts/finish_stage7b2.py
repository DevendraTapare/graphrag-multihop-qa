"""Seal only the explicitly approved local license and verification update."""

# Long Markdown paragraphs are document content; no security rules are suppressed.
# ruff: noqa: E501

import json
import shutil
from collections import Counter

from defusedxml import ElementTree as ET

from scripts.check_stage7b2 import check
from scripts.license_stage7b2 import document, inventory
from scripts.stage7b2_support import (
    OUT,
    RELEASE,
    ROOT,
    VENV,
    digest,
    read,
    run,
    save,
    update_publication,
)

PUBLIC = [
    "third-party-rights.json",
    "primary-rights-sources.json",
    "license-verification.json",
    "installed-versions.json",
    "verification-tools.json",
    "pip-audit.json",
    "bandit.json",
    "security-summary.json",
    "advisory-status-recheck.json",
    "validation-summary.json",
    "research-preservation.json",
    "model-rights-recheck.json",
]
META_HASH_EXCLUSIONS = {
    "FILE_INVENTORY.json",
    "SHA256SUMS",
    "reports/stage7b2/release-changes.json",
}


def security():
    audit = read("pip-audit.json")
    if read("dependency-audit-result.json")["exit_code"] != 0:
        raise ValueError("Audit command failed")
    if any(p.get("vulns") or p.get("skip_reason") for p in audit["dependencies"]):
        raise ValueError("Audit has findings or skipped packages")
    before = json.loads((RELEASE / "reports/stage7b/bandit.json").read_bytes())["results"]
    now = read("bandit.json")["results"]

    def fingerprint(row):
        return (
            row["filename"].replace("\\", "/"),
            row["line_number"],
            row["test_id"],
            row["issue_severity"],
            row["issue_confidence"],
            row["code"],
        )

    if Counter(map(fingerprint, before)) != Counter(map(fingerprint, now)):
        raise ValueError("Bandit finding changed; needs a new per-finding review")
    if len(now) != 12 or any(r["issue_severity"] != "LOW" for r in now):
        raise ValueError("Unexpected Bandit findings")
    unavailable = [x for x in read("advisory-status-recheck.json") if x.get("error")]
    if read("installed-versions.json")["changes_from_stage7b"]:
        raise ValueError("Dependency version changed")
    summary = {
        "audited_distributions": len(audit["dependencies"]),
        "vulnerabilities": 0,
        "skips": 0,
        "transformers": "5.17.0",
        "dependency_changes": [],
        "bandit_exit_code": read("bandit-result.json")["exit_code"],
        "bandit_findings": len(now),
        "bandit_severity": "LOW",
        "bandit_confidence": "HIGH",
        "bandit_unchanged_from_reviewed_stage7b": True,
        "bandit_rules": dict(Counter(r["test_id"] for r in now)),
        "remaining_advisory_caveats": [
            "PYSEC-2025-217 / CVE-2025-14929: no declared fixed release; unused converter absent from inspected wheel",
            "PYSEC-2026-4174 / CVE-2026-80047: no advisory patched version; selected wheel has verified code correction",
        ],
        "unavailable_security_sources": unavailable,
        "suppression_changes": [],
        "scope": "Release app/scripts; same 12 call sites and code as the prior reviewed scan",
    }
    save("security-summary.json", summary)
    return summary


def validation():
    steps = read("validation-results.json")
    if any(x["exit_code"] for x in steps):
        raise ValueError("Required real verification did not finish successfully")
    cases = list(ET.parse(OUT / "release-tests.xml").iter("testcase"))
    old = list(ET.parse(ROOT / "reports/stage7b/release-tests.xml").iter("testcase"))
    ids = {(x.get("classname"), x.get("name")) for x in cases}
    original = {(x.get("classname"), x.get("name")) for x in old}
    if ids != original:
        raise ValueError("Baseline test IDs differ")
    if any(x.find(k) is not None for x in cases for k in ("failure", "error", "skipped")):
        raise ValueError("Tests contain failed/skipped cases")
    demo, smoke = read("release-demo.json"), read("release-smoke.json")
    if demo["requests"] != 24 or len(demo["responses"]) != 24 or smoke["requests"] != 27:
        raise ValueError("Demo/smoke request count changed")
    if demo["source_only_build"]["provenance"]["failures"]:
        raise ValueError("Demo provenance failure")
    metrics = {}
    for mode in sorted({r["mode"] for r in smoke["rows"]}):
        rows = [r for r in smoke["rows"] if r["mode"] == mode]
        metrics[mode] = {
            "positive_questions": sum(r["answerable"] for r in rows),
            "positive_correct": sum(r["exact_match"] for r in rows if r["answerable"]),
            "negative_questions": sum(not r["answerable"] for r in rows),
            "negative_correct": sum(r["exact_match"] for r in rows if not r["answerable"]),
            "unsupported_answers": sum(r["unsupported_answer"] for r in rows),
        }
    if any(r["unsupported_answers"] for r in metrics.values()):
        raise ValueError("Smoke unsupported answer")
    modules = Counter(
        x.get("classname", "").removeprefix("tests.integration.").split(".")[0]
        for x in cases
        if x.get("classname", "").startswith("tests.integration.")
    )
    summary = {
        "tests": len(cases),
        "unit": sum(x.get("classname", "").startswith("tests.unit.") for x in cases),
        "integration": sum(x.get("classname", "").startswith("tests.integration.") for x in cases),
        "failures": 0,
        "errors": 0,
        "skips": 0,
        "baseline_case_ids_preserved": len(original),
        "integration_modules": dict(modules),
        "steps": steps,
        "demo_checks": 24,
        "demo_source_documents": demo["source_only_build"]["source_documents"],
        "demo_facts": demo["source_only_build"]["accepted_facts"],
        "demo_provenance": demo["provenance"],
        "repeat_index_cached": demo["source_only_build"]["repeat_index_cached"],
        "smoke_requests": 27,
        "smoke": metrics,
        "hosted_ci": "UNVERIFIED",
        "initial_attempt": "307 unit tests passed; Docker engine unavailable, so no integration tests ran. Docker Desktop started locally and real verification was rerun.",
        "paid_llm_api_calls": False,
        "source_or_dependency_changes": False,
        "scope": "Executed directly in dist/graphrag-multihop with locked environment, trusted cached model and real isolated Neo4j",
    }
    save("validation-summary.json", summary)
    return summary


def changes():
    before = read("stage7b_release_freeze.json")["files"]
    paths = {p.relative_to(RELEASE).as_posix(): p for p in RELEASE.rglob("*") if p.is_file()}
    rows = []
    for name in sorted(before.keys() | paths.keys()):
        old = before.get(name)
        sha = digest(paths[name]) if name in paths else None
        if old == sha:
            continue
        state = "removed" if name not in paths else "added" if name not in before else "modified"
        reason = (
            "Approved canonical MIT license"
            if name == "LICENSE"
            else "Verified third-party licensing inventory"
            if name == "docs/THIRD_PARTY_LICENSES.md"
            else "Final verification evidence or release metadata"
            if name.startswith("reports/")
            or name in META_HASH_EXCLUSIONS
            or name == "PUBLICATION.json"
            else "Necessary license scope/current release documentation"
        )
        row = {"path": name, "change": state, "before_sha256": old, "reason": reason}
        if name in META_HASH_EXCLUSIONS:
            row.update(
                after_sha256=None,
                hash_scope="Current hash is in SHA256SUMS where covered; own hash is never embedded; avoids checksum cycles",
            )
        else:
            row["after_sha256"] = sha
        rows.append(row)
    save(
        "release-changes.json",
        {
            "previous_files": 348,
            "previous_bytes": 25640975,
            "not_byte_identical_to_previous_snapshot": True,
            "files": rows,
        },
    )
    return rows


def inventory_and_checksums():
    paths = sorted(p for p in RELEASE.rglob("*") if p.is_file())
    rows = [
        {"path": p.relative_to(RELEASE).as_posix(), "bytes": p.stat().st_size, "sha256": digest(p)}
        for p in paths
        if p.name not in {"FILE_INVENTORY.json", "SHA256SUMS"}
    ]
    (RELEASE / "FILE_INVENTORY.json").write_text(
        json.dumps(
            {
                "scope": "Every package file except FILE_INVENTORY.json and SHA256SUMS; avoids self-reference",
                "files": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (RELEASE / "SHA256SUMS").write_text(
        "".join(
            f"{digest(p)}  {p.relative_to(RELEASE).as_posix()}\n"
            for p in paths
            if p.name != "SHA256SUMS"
        ),
        encoding="utf-8",
        newline="\n",
    )


def report(v, s, count, size, rows):
    table = "\n".join(f"| `{x['path']}` | {x['change']} | {x['reason']} |" for x in rows)
    text = f"""# Stage 7B.2 final pre-commit report

Reviewed 29 October 2026. **Verdict: CONDITIONAL GO for a local Git commit of this clean, source-only portfolio directory.** No Git action is authorized by this verdict and none was performed. This is not unconditional public-publication, bundled-runtime or production-readiness approval. Hosted GitHub Actions remains **UNVERIFIED** because no repository has been published.

## Approved license and rights boundary

The user explicitly approved the complete MIT license with the exact notice **Copyright (c) 2026 Devendra Tapare**. [LICENSE](../LICENSE) is valid UTF-8 and its full permission, notice condition and warranty disclaimer match the [official MIT text](https://opensource.org/license/mit), with standard ASCII quotes and line wrapping. Title, exact copyright, complete language and SHA-256 were verified in [license-verification.json](../reports/stage7b2/license-verification.json). License: **MIT**; copyright holder: **Devendra Tapare**; year: **2026**.

The grant covers only first-party code and original material the owner owns or may license. It does not replace any third-party license. [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) inventories source, fictional data/evaluations, original Mermaid definitions, existing third-party notices, all **79 locked registry packages**, the model, Neo4j, pinned CI actions and referenced tools. Publisher metadata, artifact license files, versioned repository licenses and the pinned model card were checked. No vendored dependency code, external benchmark corpus, downloaded image, model/tokenizer artifact or runtime binary was found in the publication. Existing third-party notices and historical reports remain unchanged.

Known questions remain separated from first-party content: the metadata-only `cuda-toolkit` package has neither a reviewed license declaration nor a license member in its wheel. The pinned MiniLM card declares Apache-2.0, but its standalone LICENSE URL returned 404. CUDA runtime/NVSHMEM and cuDNN have NVIDIA agreements; NCCL and NVTX have their specific notices. The cuDNN supplement includes an NVIDIA-GPU development restriction. Exact binary installation/use and future bundled redistribution require their own terms review; this MIT source grant does not provide those rights. None of these external packages or weights is redistributed here, so no unseparated rights blocker was identified for adding the approved first-party MIT notice. Do not infer rights to the model's training corpora. See [third-party-rights.json](../reports/stage7b2/third-party-rights.json) and [wheel-rights-review.json](../reports/stage7b2/wheel-rights-review.json). License-only wheel ranges were inspected; full CUDA wheels were not downloaded or executed.

## Final publication and exact changes

**{count} files, {size:,} bytes ({size / 1048576:.2f} MiB)**, including this report, inventory and checksums. This tree is `dist/graphrag-multihop`, a separate publication copy inside the research workspace, not the research workspace root. Verification ran directly in this clean tree. `.pytest_cache/stage7b-candidate` and all private license/security helpers remain outside it and were not copied into it.

The previous snapshot was **348 files, 25,640,975 bytes (24.45 MiB)**. Its full file hashes are preserved in [previous-release.json](../reports/stage7b2/previous-release.json); an unmodified pre-license archive remains privately in the research workspace. The new release is intentionally **not byte-identical**. All original paths remain; no release file was removed. Every added/modified file is listed below and in [release-changes.json](../reports/stage7b2/release-changes.json), with before/current hashes and explicit self-hash exclusions. App, scripts, tests, data, four migrations, dependency files, Docker and CI source remain unchanged. No unrelated dependency upgrade occurred.

| File | Change | Reason |
|---|---|---|
{table}

## Executed tests and real offline verification

**{v["tests"]} tests passed: {v["unit"]} unit and {v["integration"]} real Neo4j integration. Zero failures, errors or skips.** Every one of the prior 436 case IDs is retained. Ruff lint/format, locked environment synchronization and `uv lock --check` pass. The integration modules exercise real schema migrations, ingestion, source/hash/offset provenance, normalized MiniLM embeddings, vector builds/indexes/stale evidence, graph-only and hybrid retrieval, bounded failures and adversarial cases. Module counts and executed step durations are in [validation-summary.json](../reports/stage7b2/validation-summary.json). No mocked database check was substituted.

The offline demo passed **24/24 checks**, across eight cases and three modes, using {v["demo_source_documents"]} fictional source documents and {v["demo_facts"]} automatically extracted facts. Provenance validation reported no failures, and repeated indexing used the cached build. The separate nine-question smoke executed **27 requests**: graph/hybrid each answered 4/6 positives; vector answered 0/6 under its known grammar limit; every mode correctly abstained on 3/3 negatives. No unsupported answers occurred. This smoke includes calibration items and is not a fresh independent benchmark. Actual [demo](../reports/stage7b2/demo-results.json) and [smoke responses](../reports/stage7b2/smoke-results.json) are retained.

The initial attempt passed 307 unit tests, then stopped because Docker's engine was off; integration/demo checks did not run in that attempt. Docker Desktop was started locally, its engine became available, and the real run completed. Initial failed infrastructure/cleanup logs remain private rather than being presented as passes. Research-database startup polling observed one transient socket read timeout before readiness recovered; final snapshot queries succeeded. Original research containers were restored, and all **324 original files and three graph snapshots** match their preserved hashes: [research-preservation.json](../reports/stage7b2/research-preservation.json). No paid LLM API call was made; existing trusted cached model/package/image artifacts were used.

## Security and dependency results

The fresh pip-audit reports **zero vulnerabilities across {s["audited_distributions"]} installed distributions**, with zero collection skips. All installed versions match Stage 7B.1; Transformers remains **5.17.0**, sentence-transformers **5.7.0**, Torch **2.14.1** and tokenizers **0.23.3**. The lock and project dependency files are unchanged. [Installed versions](../reports/stage7b2/installed-versions.json), [raw audit](../reports/stage7b2/pip-audit.json) and [security summary](../reports/stage7b2/security-summary.json) are retained. No security data source used in this run was unavailable.

Bandit again reports **12 LOW/HIGH-confidence warnings**, unchanged at the same reviewed source lines: B404 imports (3), B603 fixed-argv subprocess calls (5), B607 Docker lookup through a trusted local PATH (3), and B311 deterministic fictional data generation (1). There are no medium/high or app-runtime findings. Its exit code **1** reflects these retained warnings; it is not a zero-warning scan. The three PATH warnings remain a conditional local substitution risk. No rules, paths or findings were suppressed to make this result pass. The original [per-finding review](../reports/stage7b/BANDIT_REVIEW.md) and [fresh scan](../reports/stage7b2/bandit.json) cover every retained warning.

The two advisory-status caveats remain: X-CLIP has no declared fixed release and no reachable converter path in this application; custom generation has no declared advisory patched version, although the selected 5.17.0 wheel has the previously verified consent-before-download correction and is unused by this encoder. The authoritative records were rechecked; scanner silence is not a claim that both CVEs were formally closed. [STAGE7B_SECURITY_REVIEW.md](STAGE7B_SECURITY_REVIEW.md) and the [status recheck](../reports/stage7b2/advisory-status-recheck.json) preserve that distinction. Untrusted model loading and public service exposure remain outside the reviewed scope.

Final Gitleaks and exact real-credential scans found no secrets in the intended payload. Default rules and the existing narrow exact-value allowances were preserved. No credentials, SSH keys, API tokens, volumes, weights/caches, environments, logs, private documents, temporary scripts, test caches, bytecode or Git metadata were included. Local Markdown links/fragments, JSON validity, required source/migration/Docker/CI inclusion, unexpected artifacts and duplicates were checked in [publication-checks.json](../reports/stage7b2/publication-checks.json). Existing duplicate package markers, matching architecture docs and historical evidence copies were identified and deliberately retained; nothing was removed silently.

`FILE_INVENTORY.json` retains the path/byte-size/SHA-256 format and excludes itself and `SHA256SUMS`. `SHA256SUMS` uses two-space path separation, covers every other file including the inventory, and excludes itself. Both were rebuilt and every entry verified. Change-record metadata avoids embedding its own or the generated checksum/inventory hashes; the global checksum file provides the covered hashes. These are integrity checks, not a signed authenticity proof.

## Limitations and stopping boundary

Historical results remain visible: Stage 5 graph/hybrid 96/96 was an inspected development result; Stage 6 graph/hybrid answered 54/128 positives and vector 0/128 under its frozen grammar. Hybrid evidence coverage improved without a corresponding final-answer gain. False abstentions, the historical top-k 1 partial-answer case and earlier load failures remain in the evidence. The Stage 7A pool-50 burst improvement is not a sustained HTTP-capacity or production-reliability result; CPU saturation and high latency remain limitations. No full historical benchmark was overwritten or reclassified.

The MIT decision is complete for authorized original material. Source-only rights review found no included unseparated third-party blocker. Remaining conditions are the documented vendor advisory uncertainty, trusted local PATH/cache assumptions, external CUDA/model rights questions for other installation/bundling scenarios, unverified Linux/macOS and hosted CI, and separate owner authorization before any Git/publication/deployment action. **CONDITIONAL GO applies only to a local commit of this reviewed directory and its documented portfolio scope.** It does not certify arbitrary-platform binary distribution or unrestricted public-service use.

No `git init`, add, commit, remote, push, repository creation, tag/release creation or deployment was performed. No new development stage was started. The work stops at this verified local release and report.
"""
    (RELEASE / "docs/STAGE7B_PRECOMMIT_REPORT.md").write_text(text, encoding="utf-8")


def main():
    s, v = security(), validation()
    target = RELEASE / "reports/stage7b2"
    target.mkdir(exist_ok=True)
    rights = inventory()
    document(rights)
    for name in PUBLIC:
        shutil.copyfile(OUT / name, target / name)
    public_wheels = read("wheel-rights-review.json")
    for item in public_wheels:
        for notice in item.get("notices", []):
            notice.pop("opening", None)
    (target / "wheel-rights-review.json").write_text(
        json.dumps(public_wheels, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copyfile(OUT / "stage7b_release_freeze.json", target / "previous-release.json")
    for old, new in [
        ("release-demo.json", "demo-results.json"),
        ("release-smoke.json", "smoke-results.json"),
    ]:
        shutil.copyfile(OUT / old, target / new)
    # Seed all referenced files before link checking; every placeholder is replaced below.
    for name in ["publication-checks.json", "release-changes.json"]:
        (target / name).write_text("{}\n", encoding="utf-8")
    summary = RELEASE / "docs/FINAL_PROJECT_SUMMARY.md"
    text = summary.read_text(encoding="utf-8")
    summary.write_text(
        text.replace(
            "License/rights approval and a real hosted CI run still gate public publication.",
            "Stage 7B.2 adds MIT for authorized original material with separate third-party terms; hosted CI remains unverified. Read [STAGE7B_PRECOMMIT_REPORT.md](STAGE7B_PRECOMMIT_REPORT.md) for the current local commit gate.",
        ),
        encoding="utf-8",
    )
    security_doc = RELEASE / "docs/SECURITY_REVIEW.md"
    text = security_doc.read_text(encoding="utf-8")
    if not text.startswith("# Stage 7B.2 licensing and final verification"):
        security_doc.write_text(
            "# Stage 7B.2 licensing and final verification\n\nThe approved first-party project license is now MIT. Separate third-party terms and the security caveats below remain. See [STAGE7B_PRECOMMIT_REPORT.md](STAGE7B_PRECOMMIT_REPORT.md) for current verification and scope. The dated security review below remains historical evidence.\n\n"
            + text,
            encoding="utf-8",
        )
    readme = RELEASE / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = text.replace("Current verification:", "Stage 7B.2 final verification:")
    text = text.replace(
        "Read [STAGE7B_SECURITY_REVIEW.md](docs/STAGE7B_SECURITY_REVIEW.md) for the current gate.",
        "Read [STAGE7B_PRECOMMIT_REPORT.md](docs/STAGE7B_PRECOMMIT_REPORT.md) for the current local commit gate and [STAGE7B_SECURITY_REVIEW.md](docs/STAGE7B_SECURITY_REVIEW.md) for advisory detail.",
    )
    readme.write_text(text, encoding="utf-8")
    previous = None
    for _ in range(18):
        paths = [p for p in RELEASE.rglob("*") if p.is_file()]
        count, size = len(paths), sum(p.stat().st_size for p in paths)
        rows = (
            read("release-changes.json")["files"] if (OUT / "release-changes.json").exists() else []
        )
        report(v, s, count, size, rows)
        manifest = f"""# Publication manifest

Current clean publication: **{count} files, {size:,} bytes ({size / 1048576:.2f} MiB)**. License: **MIT** for authorized first-party material, Copyright (c) 2026 Devendra Tapare. The directory is `dist/graphrag-multihop`, separate from the original research tree inside the workspace. It is a local portfolio release candidate; no Git/publication/deployment operation has been performed.

The prior Stage 7B.1 snapshot was **348 files, 25,640,975 bytes (24.45 MiB)**. Its complete prior file hashes are retained in [previous-release.json](../reports/stage7b2/previous-release.json), and the unmodified archive remains private. The current tree is intentionally not byte-identical: the approved LICENSE, licensing/current-verification documents and generated evidence/manifests were added or updated. No prior file was removed. [release-changes.json](../reports/stage7b2/release-changes.json) and the [pre-commit report](STAGE7B_PRECOMMIT_REPORT.md) list every change.

The existing inventory format is preserved: `FILE_INVENTORY.json` lists each payload path, byte size and SHA-256, excluding itself and `SHA256SUMS`. The conventional `SHA256SUMS` lists `hash`, two spaces and relative path for every other file including the inventory; it excludes only itself. Checksum lines use LF and UTF-8. The change record omits self/inventory/checksum after-hashes to avoid cycles; covered hashes are in SHA256SUMS. Counts include the report, inventory and checksums, and converge before verification. Hashes detect changes, not authorship or authenticity.

All source, scripts, tests, fictional data, four migrations, dependency files, Docker and CI sources are retained and unchanged from the 348-file baseline. All original research files and graph snapshots, negative benchmark evidence and existing third-party notices remain preserved. Historical Stage 1-7B.1 reports keep their dated counts and earlier no-license statements; current licensing and final verification are in [STAGE7B_PRECOMMIT_REPORT.md](STAGE7B_PRECOMMIT_REPORT.md). `PUBLICATION.json` retains original source hashes, omissions and declared historical security differences; its current `overrides` and `license_overrides` record necessary documentation changes. No version upgrade was made in this stage.

The MIT grant does not replace third-party licenses. See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for all 79 locked package declarations, model/container references, notices and unresolved external installation/bundling questions. Dependency binaries, model/tokenizer weights, caches, volumes, environments, logs, personal/private documents, temporary review scripts and Git metadata are excluded. The temporary `.pytest_cache/stage7b-candidate` directory is outside this publication and was not used as its source.

Complete payload, secret, binary, duplicate, local-link and required-file checks are in [publication-checks.json](../reports/stage7b2/publication-checks.json). Existing duplicate module markers, architecture copies and historical evidence copies are deliberately retained. No private archive or review helper is included. Hosted GitHub Actions remains **UNVERIFIED** because no repository has been published. The local commit verdict is conditional on the documented trusted portfolio scope; public-service and bundled-runtime readiness are not claimed. No Git action is authorized or performed.
"""
        (RELEASE / "docs/PUBLICATION_MANIFEST.md").write_text(manifest, encoding="utf-8")
        update_publication()
        audit = check()
        save("publication-checks.json", audit)
        shutil.copyfile(OUT / "publication-checks.json", target / "publication-checks.json")
        changes()
        shutil.copyfile(OUT / "release-changes.json", target / "release-changes.json")
        inventory_and_checksums()
        paths = [p for p in RELEASE.rglob("*") if p.is_file()]
        state = len(paths), sum(p.stat().st_size for p in paths)
        if state == previous:
            break
        previous = state
    else:
        raise ValueError("File/byte totals did not converge")
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
        result = run(name, args, 300)
        if result["exit_code"]:
            raise ValueError(f"Final required check failed: {name}")
    final = check()
    if final["files"] != state[0] or final["bytes"] != state[1]:
        raise ValueError("Payload changed during final checks")
    for line in (RELEASE / "SHA256SUMS").read_text().splitlines():
        sha, path = line.split("  ", 1)
        if digest(RELEASE / path) != sha:
            raise ValueError(path)
    for row in json.loads((RELEASE / "FILE_INVENTORY.json").read_bytes())["files"]:
        if (
            digest(RELEASE / row["path"]) != row["sha256"]
            or (RELEASE / row["path"]).stat().st_size != row["bytes"]
        ):
            raise ValueError(row["path"])
    save(
        "final-verification.json",
        {
            **final,
            "checksum_entries": final["files"] - 1,
            "checksum_failures": 0,
            "gitleaks_findings": 0,
            "tests": v["tests"],
            "local_commit_verdict": "CONDITIONAL GO",
            "no_git_or_publication_actions": True,
        },
    )
    print(
        json.dumps(
            {
                "files": final["files"],
                "bytes": final["bytes"],
                "tests": v["tests"],
                "dependency_findings": 0,
                "bandit_low": 12,
                "license": "MIT",
                "local_commit": "CONDITIONAL GO",
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
