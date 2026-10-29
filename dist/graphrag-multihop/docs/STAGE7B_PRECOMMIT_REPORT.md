# Stage 7B.2 final pre-commit report

Reviewed 29 October 2026. **Verdict: CONDITIONAL GO for a local Git commit of this clean, source-only portfolio directory.** No Git action is authorized by this verdict and none was performed. This is not unconditional public-publication, bundled-runtime or production-readiness approval. Hosted GitHub Actions remains **UNVERIFIED** because no repository has been published.

## Approved license and rights boundary

The user explicitly approved the complete MIT license with the exact notice **Copyright (c) 2026 Devendra Tapare**. [LICENSE](../LICENSE) is valid UTF-8 and its full permission, notice condition and warranty disclaimer match the [official MIT text](https://opensource.org/license/mit), with standard ASCII quotes and line wrapping. Title, exact copyright, complete language and SHA-256 were verified in [license-verification.json](../reports/stage7b2/license-verification.json). License: **MIT**; copyright holder: **Devendra Tapare**; year: **2026**.

The grant covers only first-party code and original material the owner owns or may license. It does not replace any third-party license. [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) inventories source, fictional data/evaluations, original Mermaid definitions, existing third-party notices, all **79 locked registry packages**, the model, Neo4j, pinned CI actions and referenced tools. Publisher metadata, artifact license files, versioned repository licenses and the pinned model card were checked. No vendored dependency code, external benchmark corpus, downloaded image, model/tokenizer artifact or runtime binary was found in the publication. Existing third-party notices and historical reports remain unchanged.

Known questions remain separated from first-party content: the metadata-only `cuda-toolkit` package has neither a reviewed license declaration nor a license member in its wheel. The pinned MiniLM card declares Apache-2.0, but its standalone LICENSE URL returned 404. CUDA runtime/NVSHMEM and cuDNN have NVIDIA agreements; NCCL and NVTX have their specific notices. The cuDNN supplement includes an NVIDIA-GPU development restriction. Exact binary installation/use and future bundled redistribution require their own terms review; this MIT source grant does not provide those rights. None of these external packages or weights is redistributed here, so no unseparated rights blocker was identified for adding the approved first-party MIT notice. Do not infer rights to the model's training corpora. See [third-party-rights.json](../reports/stage7b2/third-party-rights.json) and [wheel-rights-review.json](../reports/stage7b2/wheel-rights-review.json). License-only wheel ranges were inspected; full CUDA wheels were not downloaded or executed.

## Final publication and exact changes

**369 files, 26,482,122 bytes (25.26 MiB)**, including this report, inventory and checksums. This tree is `dist/graphrag-multihop`, a separate publication copy inside the research workspace, not the research workspace root. Verification ran directly in this clean tree. `.pytest_cache/stage7b-candidate` and all private license/security helpers remain outside it and were not copied into it.

The previous snapshot was **348 files, 25,640,975 bytes (24.45 MiB)**. Its full file hashes are preserved in [previous-release.json](../reports/stage7b2/previous-release.json); an unmodified pre-license archive remains privately in the research workspace. The new release is intentionally **not byte-identical**. All original paths remain; no release file was removed. Every added/modified file is listed below and in [release-changes.json](../reports/stage7b2/release-changes.json), with before/current hashes and explicit self-hash exclusions. App, scripts, tests, data, four migrations, dependency files, Docker and CI source remain unchanged. No unrelated dependency upgrade occurred.

| File | Change | Reason |
|---|---|---|
| `FILE_INVENTORY.json` | modified | Final verification evidence or release metadata |
| `LICENSE` | added | Approved canonical MIT license |
| `PUBLICATION.json` | modified | Final verification evidence or release metadata |
| `README.md` | modified | Necessary license scope/current release documentation |
| `SHA256SUMS` | modified | Final verification evidence or release metadata |
| `docs/FINAL_PROJECT_SUMMARY.md` | modified | Necessary license scope/current release documentation |
| `docs/PUBLICATION_MANIFEST.md` | modified | Necessary license scope/current release documentation |
| `docs/SECURITY_REVIEW.md` | modified | Necessary license scope/current release documentation |
| `docs/STAGE7B_PRECOMMIT_REPORT.md` | added | Necessary license scope/current release documentation |
| `docs/THIRD_PARTY_LICENSES.md` | added | Verified third-party licensing inventory |
| `docs/THIRD_PARTY_NOTICES.md` | modified | Necessary license scope/current release documentation |
| `reports/stage7b2/advisory-status-recheck.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/bandit.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/demo-results.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/installed-versions.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/license-verification.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/model-rights-recheck.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/pip-audit.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/previous-release.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/primary-rights-sources.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/publication-checks.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/release-changes.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/research-preservation.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/security-summary.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/smoke-results.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/third-party-rights.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/validation-summary.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/verification-tools.json` | added | Final verification evidence or release metadata |
| `reports/stage7b2/wheel-rights-review.json` | added | Final verification evidence or release metadata |

## Executed tests and real offline verification

**436 tests passed: 307 unit and 129 real Neo4j integration. Zero failures, errors or skips.** Every one of the prior 436 case IDs is retained. Ruff lint/format, locked environment synchronization and `uv lock --check` pass. The integration modules exercise real schema migrations, ingestion, source/hash/offset provenance, normalized MiniLM embeddings, vector builds/indexes/stale evidence, graph-only and hybrid retrieval, bounded failures and adversarial cases. Module counts and executed step durations are in [validation-summary.json](../reports/stage7b2/validation-summary.json). No mocked database check was substituted.

The offline demo passed **24/24 checks**, across eight cases and three modes, using 12 fictional source documents and 30 automatically extracted facts. Provenance validation reported no failures, and repeated indexing used the cached build. The separate nine-question smoke executed **27 requests**: graph/hybrid each answered 4/6 positives; vector answered 0/6 under its known grammar limit; every mode correctly abstained on 3/3 negatives. No unsupported answers occurred. This smoke includes calibration items and is not a fresh independent benchmark. Actual [demo](../reports/stage7b2/demo-results.json) and [smoke responses](../reports/stage7b2/smoke-results.json) are retained.

The initial attempt passed 307 unit tests, then stopped because Docker's engine was off; integration/demo checks did not run in that attempt. Docker Desktop was started locally, its engine became available, and the real run completed. Initial failed infrastructure/cleanup logs remain private rather than being presented as passes. Research-database startup polling observed one transient socket read timeout before readiness recovered; final snapshot queries succeeded. Original research containers were restored, and all **324 original files and three graph snapshots** match their preserved hashes: [research-preservation.json](../reports/stage7b2/research-preservation.json). No paid LLM API call was made; existing trusted cached model/package/image artifacts were used.

## Security and dependency results

The fresh pip-audit reports **zero vulnerabilities across 60 installed distributions**, with zero collection skips. All installed versions match Stage 7B.1; Transformers remains **5.17.0**, sentence-transformers **5.7.0**, Torch **2.14.1** and tokenizers **0.23.3**. The lock and project dependency files are unchanged. [Installed versions](../reports/stage7b2/installed-versions.json), [raw audit](../reports/stage7b2/pip-audit.json) and [security summary](../reports/stage7b2/security-summary.json) are retained. No security data source used in this run was unavailable.

Bandit again reports **12 LOW/HIGH-confidence warnings**, unchanged at the same reviewed source lines: B404 imports (3), B603 fixed-argv subprocess calls (5), B607 Docker lookup through a trusted local PATH (3), and B311 deterministic fictional data generation (1). There are no medium/high or app-runtime findings. Its exit code **1** reflects these retained warnings; it is not a zero-warning scan. The three PATH warnings remain a conditional local substitution risk. No rules, paths or findings were suppressed to make this result pass. The original [per-finding review](../reports/stage7b/BANDIT_REVIEW.md) and [fresh scan](../reports/stage7b2/bandit.json) cover every retained warning.

The two advisory-status caveats remain: X-CLIP has no declared fixed release and no reachable converter path in this application; custom generation has no declared advisory patched version, although the selected 5.17.0 wheel has the previously verified consent-before-download correction and is unused by this encoder. The authoritative records were rechecked; scanner silence is not a claim that both CVEs were formally closed. [STAGE7B_SECURITY_REVIEW.md](STAGE7B_SECURITY_REVIEW.md) and the [status recheck](../reports/stage7b2/advisory-status-recheck.json) preserve that distinction. Untrusted model loading and public service exposure remain outside the reviewed scope.

Final Gitleaks and exact real-credential scans found no secrets in the intended payload. Default rules and the existing narrow exact-value allowances were preserved. No credentials, SSH keys, API tokens, volumes, weights/caches, environments, logs, private documents, temporary scripts, test caches, bytecode or Git metadata were included. Local Markdown links/fragments, JSON validity, required source/migration/Docker/CI inclusion, unexpected artifacts and duplicates were checked in [publication-checks.json](../reports/stage7b2/publication-checks.json). Existing duplicate package markers, matching architecture docs and historical evidence copies were identified and deliberately retained; nothing was removed silently.

`FILE_INVENTORY.json` retains the path/byte-size/SHA-256 format and excludes itself and `SHA256SUMS`. `SHA256SUMS` uses two-space path separation, covers every other file including the inventory, and excludes itself. Both were rebuilt and every entry verified. Change-record metadata avoids embedding its own or the generated checksum/inventory hashes; the global checksum file provides the covered hashes. These are integrity checks, not a signed authenticity proof.

## Limitations and stopping boundary

Historical results remain visible: Stage 5 graph/hybrid 96/96 was an inspected development result; Stage 6 graph/hybrid answered 54/128 positives and vector 0/128 under its frozen grammar. Hybrid evidence coverage improved without a corresponding final-answer gain. False abstentions, the historical top-k 1 partial-answer case and earlier load failures remain in the evidence. The Stage 7A pool-50 burst improvement is not a sustained HTTP-capacity or production-reliability result; CPU saturation and high latency remain limitations. No full historical benchmark was overwritten or reclassified.

The MIT decision is complete for authorized original material. Source-only rights review found no included unseparated third-party blocker. Remaining conditions are the documented vendor advisory uncertainty, trusted local PATH/cache assumptions, external CUDA/model rights questions for other installation/bundling scenarios, unverified Linux/macOS and hosted CI, and separate owner authorization before any Git/publication/deployment action. **CONDITIONAL GO applies only to a local commit of this reviewed directory and its documented portfolio scope.** It does not certify arbitrary-platform binary distribution or unrestricted public-service use.

No `git init`, add, commit, remote, push, repository creation, tag/release creation or deployment was performed. No new development stage was started. The work stops at this verified local release and report.
