"""Write the final review only after the mandatory real validation succeeds."""

# Long Markdown prose is emitted as a document, not executable statements.
# ruff: noqa: E501

import json

from scripts.stage7b_support import OUT, ROOT


def read(name):
    return json.loads((OUT / name).read_bytes())


def make_report(summary):
    findings = read("advisory-review.json")["findings"]
    table = [
        "| Advisory and authoritative source | Vulnerable range / declared fix | Severity | Reachability and final disposition |",
        "|---|---|---|---|",
    ]
    for row in findings:
        aliases = ", ".join(row["aliases"])
        table.append(
            f"| [{row['id']}]({row['source']}); {aliases}; {row['records']} audit record(s) "
            f"| {row['vulnerable_range']} **Declared fix: {row['fixed_version'] or 'none published'}.** "
            f"| {row['severity']}, CVSS {row['cvss']} "
            f"| {row['reachable']} {row['disposition']} {row['mitigation']} |"
        )
    changes = ["| Package | Before | After |", "|---|---|---|"]
    changes.extend(
        f"| {r['package']} | {r['before'] or 'absent'} | {r['after'] or 'removed'} |"
        for r in read("dependency-changes.json")
    )
    text = f"""# Stage 7B.1 dependency security review and release gate

Reviewed 29 October 2026. **Publication verdict: CONDITIONAL GO for a source-only, trusted local portfolio demonstration.** The dependency migration removes every finding reported by the current audit. Two advisories still lack an official fixed-version declaration, so this report distinguishes measured mitigations from vendor-confirmed closure. The package is not production ready.

**Recommendation:** the reviewed dependency state does not require a further security-only delay for this restricted portfolio scope. Public publication must still wait for the owner's license/rights decision and a real hosted CI result. Keep the advisory limitations visible. Public service deployment, arbitrary model loading or training/checkpoint conversion would need a new review and currently fail this gate. No publication action was performed or authorized by this review.

## Scope and preserved evidence

The candidate is `dist/graphrag-multihop`. Stage 7A's 328-file candidate was hashed and archived before any edits. Changes were tested in an isolated copy with a new virtual environment and dedicated Neo4j volumes. The research environment's dependency files remain frozen for reproducibility; **the updated files are the publication candidate's `pyproject.toml` and `uv.lock`**. Do not use the historical environment as the security-reviewed release.

All 324 original research files, the original app/data/migration bytes, all historical evaluation reports and all three research graph snapshots are preserved. Historical negative accuracy and load/error evidence remains visible. The historical dependency and Bandit reports retain their original numbers and are superseded for the current package by this review. Research containers were restored after checks. Read the [preservation results](../reports/stage7b/research-preservation.json).

## Six advisories, nine records

Every original finding affects **Transformers 4.57.6**. It is both a direct project requirement and a transitive requirement of sentence-transformers. The selected release uses **Transformers 5.17.0**. Three advisory IDs occur twice in the original PyPI-service output: PYSEC-2026-2288, PYSEC-2026-2289 and PYSEC-2026-2290. That makes nine records and six unique advisories, not nine distinct vulnerabilities. See the [per-advisory machine-readable review](../reports/stage7b/advisory-review.json).

Severity below comes from the cited GitHub reviewed advisory or, for X-CLIP, the CNA/ZDI record. These are upstream CVSS scores, not a calculated project-specific exploitability score. No exploit payload or untrusted model was executed.

{chr(10).join(table)}

Remaining vulnerability status: the current audit reports zero findings. Four original advisory IDs are resolved by declared patched versions. X-CLIP retains an unconfirmed vendor fix status with no application path to its converter; custom generation has a verified code correction but no declared advisory patched version. Those two are qualified mitigations, not unconditional CVE-closure claims.

For X-CLIP, the [CNA record](https://cveawg.mitre.org/api/cve/CVE-2025-14929) specifies an affected commit and unknown status elsewhere; the [PyPA entry](https://github.com/pypa/advisory-database/blob/main/vulns/transformers/PYSEC-2025-217.yaml) lists versions through 5.0.0rc0 but no fixed event. Neither is evidence of an official patched SemVer release. The relevant converter is absent from both inspected installed wheels. It is not called by this application. This is a reachability mitigation with residual vendor-status uncertainty, not a claim that the CVE was formally fixed.

For custom generation, the [maintainer correction](https://github.com/huggingface/transformers/commit/cbc1651) moves module download after the consent check. The 5.10.0 through 5.16.0 minor release source tags still show the old ordering, despite being outside the advisory's published upper bound. The selected [5.17.0 source](https://github.com/huggingface/transformers/blob/v5.17.0/src/transformers/generation/utils.py) has the corrected ordering, and its function matches the installed wheel. **5.17.0 is the selected verified release, not a claimed first patched version.** The advisory still says no patched version; the source check is retained separately from the audit result in [installed-source-verification.json](../reports/stage7b/installed-source-verification.json).

Reachability conclusions come from tracing `app/vector/embedding.py` and the application/script call sites. Inference uses only `sentence-transformers/all-MiniLM-L6-v2`, immutable revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU execution, local-files-only loading, offline environment flags and `trust_remote_code=False`. User questions do not select models/configs. The app does not train, convert X-CLIP checkpoints, use LightGlue, export chat templates or load custom generation code. A modified local model cache or hostile OS account remains outside this trusted-workspace boundary. The trust flag alone did not fix all of the original upstream defects.

## Smallest tested compatible dependency change

The project stays on Python 3.12 (tested interpreter 3.12.13; project constraint remains `>=3.12`). Selected Transformers 5.17.0 declares Python `>=3.10`; sentence-transformers 5.7.0 declares Transformers `>=4.41,<6`, so it can remain unchanged. Transformers is an actively used encoder backend and cannot simply be removed. The release requirement becomes `transformers>=5.17,<6`, with the exact tested 5.17.0 and artifact hashes in the lock. Future unlocked resolutions need a new audit and regression run.

The lower 5.10.0 release would address the four advisories with declared fixes, but its custom-generation source still has the reported ordering problem. The selected 5.17.0 has the maintainer correction. This avoids taking the newest 5.21 release solely because it is newer. Tokenizers and Hugging Face Hub change because the new Transformers line requires compatible versions. New Typer/Rich-related dependencies are upstream requirements. The old Requests stack becomes unused and drops out of the resolved graph. The new Hub requirements also activate hf-xet 1.7.1 on Windows; that version was already in the cross-platform lock but was absent from the old installed environment. The [installed delta](../reports/stage7b/installed-dependency-changes.json) records this separately. `defusedxml` is added only to the development group for local reporting/CI tools; its [maintainer package documentation](https://pypi.org/project/defusedxml/) explains the hardened XML parser.

{chr(10).join(changes)}

Sentence-transformers **5.7.0**, Torch **2.14.1**, Neo4j driver **6.4.1** and the Neo4j **5.26.32 Community** image stay unchanged. No `neo4j-graphrag` distribution is installed or added: this project implements its own graph retrieval on the Neo4j driver. The [installed metadata](../reports/stage7b/dependency-metadata.json) and [lock delta](../reports/stage7b/dependency-changes.json) record exact requirements and versions.

`uv lock --check` and `uv sync --locked` pass. All 79 registry package versions in the 80-entry cross-platform lock were checked against official PyPI per-version advisory metadata; no findings or query errors were returned. All **761 locked artifact hashes** match the published PyPI metadata. The remaining entry is this local project. This verifies lock metadata, not execution on every OS. The Windows installed-environment pip-audit covers 60 distributions, with zero skipped packages and zero reported vulnerabilities. See [pip-audit.json](../reports/stage7b/pip-audit.json) and [all-lock-packages-review.json](../reports/stage7b/all-lock-packages-review.json). Scanner results depend on advisory coverage and date; the two unresolved fixed-version declarations above remain disclosed.

Changing the embedding-library version changes the application's embedding/build signature. Existing vectors from the old environment must be rebuilt; the isolated checks and documented `portfolio prepare` do this. No model ID, revision, dimensions, truncation limit, graph architecture or retrieval timeout was changed.

## Every Bandit finding reviewed

The original scan reports **131 findings: 122 low and nine medium; no high findings and no app-runtime findings**. All have HIGH confidence. The final app/scripts scan reports **12 LOW findings**, all HIGH confidence, with zero medium/high and zero runtime-app findings. Bandit's nonzero exit for those 12 warnings is recorded and expected; this is a reviewed result, not a claim that the scanner passes with no findings.

| Rule | Original | Final | Disposition |
|---|---:|---:|---|
| B101 assertions | 104 | 0 | Real workflow/evidence checks could disappear under `python -O`. Replaced with explicit conditional exceptions while preserving conditions and messages. |
| B314 XML parsing | 9 | 0 | Real unnecessary parser exposure if a local JUnit file or CI artifact is replaced. All six parsing modules use defusedxml. |
| B405 XML imports | 6 | 0 | Informational import warning addressed with the associated parser change. |
| B603 subprocess calls | 5 | 5 | Current argv lists use the default `shell=False`, fixed modules/actions and local ports; no document/question input reaches these calls. Command-injection warning is a false positive for the reviewed call sites. |
| B404 subprocess imports | 3 | 3 | Import alone is not a vulnerability; each associated call was reviewed. |
| B607 partial executable path | 3 | 3 | Accepted conditional local PATH substitution risk. Requires a trusted Docker installation, PATH and workspace; no portable absolute Docker path is assumed. |
| B311 pseudo-random generator | 1 | 1 | False positive for cryptographic use: seeded fictional benchmark names, no credentials or security tokens. |

The [131-row review](../reports/stage7b/BANDIT_REVIEW.md) identifies every original file/line, rule, severity, confidence and disposition. Its [JSON companion](../reports/stage7b/bandit-review.json) gives each row's behavior, reachable local function/import, rationale, remediation and retained final line numbers. **No Bandit rules or paths were suppressed.** The final [raw scan](../reports/stage7b/bandit.json) is also retained.

The assertion changes are limited to local verification, benchmark-authoring and evidence-preservation scripts. They make no retrieval architecture change. A condition/message comparison checked all 104 original assertions. The frozen-source test allows only explicitly named security-related file overrides and still verifies the source/release hashes; app/data/migrations remain byte-identical. Seven added regression cases verify normal JUnit parsing, entity rejection, failure/error/skip rejection under optimized Python, empty results and absent integration results. All existing tests remain present.

Legacy recording/recovery scripts can operate on research volumes or overwrite reports. They are retained for inspection and historical reproducibility, and are not the clean portfolio demo workflow. Follow `DEMO_GUIDE.md` and the guarded `scripts.portfolio` commands instead. Local PATH control is a real remaining assumption, not silently classified as a false positive.

## Revalidation and actual failures

{summary["validation_text"]}

The first unit preflight did not collect tests because a relative pytest cache path triggered pytest's Windows cache-path validation. An absolute private cache path corrected the invocation. The next unit run had **303 passes and four failures**: three detected an incompatible CI exception type introduced during editing, and one detected a Windows default-decoding error in an edited Unicode test. The original AssertionError contract and original UTF-8 test data were restored. The corrected unit run passed **307/307**. Both failed-attempt logs and JUnit evidence are retained outside the publication. Ruff initially reported formatting/line-length issues during editing; formatting corrected them before the successful required checks. Two local review-helper attempts also needed AST normalization of an equivalent `not in` condition; they did not change product behavior or test results. Initial sealing also stopped on a missing self-referenced checks file; it was initialized before link validation and the seal was rerun. The release was not refreshed during that failed attempt. No failed run was discarded or counted as a success.

The full dependency, model and retrieval checks use cached trusted artifacts. No untrusted checkpoint, model/config or exploit payload was downloaded or executed. Normal package wheels came from the locked PyPI artifacts; no paid LLM call was made. Tests use a new virtual environment and real disposable Neo4j databases. Linux/macOS and GitHub-hosted execution remain unverified; no new sustained-load or full historical rebenchmark claim is made.

## Clean release and remaining conditions

{summary["publication_text"]}

Remaining limitations are: upstream advisory fixed-version/range metadata uncertainty; three accepted local Docker PATH warnings; a trusted local model cache; unauthenticated loopback-only demonstration; incomplete synthetic extraction/question grammar; unverified hosted CI and other operating systems; and the owner's unresolved project/data license and source-rights decision. The audit cannot exclude undisclosed vulnerabilities. The historical research environment still contains the old dependency versions and is preserved as evidence, not offered as the reviewed runtime.

No LICENSE file, Git commit, repository, remote, push or deployment was created. No negative benchmark evidence, original research file or graph snapshot was removed. Stop point: security review and refreshed local publication candidate only.
"""
    (ROOT / "docs/STAGE7B_SECURITY_REVIEW.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    raise SystemExit("Call make_report only with the verified final results")
