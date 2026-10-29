# Stage 7B.2 licensing and final verification

The approved first-party project license is now MIT. Separate third-party terms and the security caveats below remain. See [STAGE7B_PRECOMMIT_REPORT.md](STAGE7B_PRECOMMIT_REPORT.md) for current verification and scope. The dated security review below remains historical evidence.

# Current security gate

Stage 7B.1 supersedes the dated Stage 7A scan below. The upgraded lock's audit reports zero vulnerabilities across 60 distributions. Bandit retains 12 reviewed LOW warnings. Two advisories have no official patched-version declaration: one is outside this application's reachable functionality and the other has a verified source correction in the selected wheel. No public-service or production approval is implied. Read [STAGE7B_SECURITY_REVIEW.md](STAGE7B_SECURITY_REVIEW.md) and its per-finding evidence before publication.

## Historical Stage 7A review (unchanged text)

# Security and provenance review

Scope: the clean Stage 7A source publication, fictional data, local Docker configuration and existing API/service boundaries. This is a local portfolio review, not a penetration test, deployment approval or a guarantee that no vulnerability exists.

## Boundaries checked

| Property | Implementation/evidence | Limit |
|---|---|---|
| No arbitrary Cypher endpoint | API exposes typed question requests; fixed plan/template selection in `app/graph_rag` | Trusted local scripts and the database driver can execute their own developer-supplied queries |
| Allowlisted relationships and bounded paths | Five factual relation enums, typed endpoints, at most three hops, 128 candidates and ten answers | Larger legitimate questions can abstain |
| Source-backed facts and paths | Exact quote/offset/hash proof replay, current source/run checks and actual edge validation | Proves source support, not real-world truth or extraction completeness |
| No invented direct relationship | Graph answers follow actual paths; all accepted demo/challenge facts are auditable | Deterministic text answerer still has a known historical top-k 1 partial-set failure |
| Ambiguity fails closed | Scoped identities and unique typed start resolution; bare Lee Chen/homonym tests | Finite registry discovery is not open-world entity resolution |
| Stale evidence rejected | Versioned ingestion, vector build signatures, source publication seals and final candidate recheck | More reads; no production consistency/performance guarantee |
| Document text cannot execute code | Bounded UTF-8 loader and rule processing; user values do not become shell or Cypher code | Local workflows assume a trusted OS account and workspace |
| Safe errors and credentials | SecretStr settings, configured log redaction, fixed API errors and request IDs | Raw developer diagnostics are private and excluded |
| Restricted mutation workflow | No ingestion/mutation HTTP route; explicit local CLI preparation; publication/loopback/development guard | No authentication or authorization layer; local settings are trusted operator input |
| Local exposure | Compose binds Neo4j to loopback; API defaults to loopback | Public binding or a shared host needs a separate security design |

The real integration suite includes forged/wrong-type/missing evidence, stale source/version, orphan chunks, conflicting branches, bounded overflow, identity ambiguity, candidate revalidation races, vector publication failure and outage behavior. Stage 6 also exercised an actual filesystem junction escape. Real symlink creation was not available in that run; its branch has unit coverage. Test execution and counts are recorded separately in [STAGE7A_RELEASE_REPORT.md](STAGE7A_RELEASE_REPORT.md).

## Secret and artifact scans

Gitleaks 8.30.1 was downloaded from the [official release](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1) and verified against the published checksum. The initial default-rule scan reported ten findings: nine SHA-256 checksum lines in historical freeze records and one fictional `environment-secret-123` unit-test input. Each was reviewed against its source line. The publication `.gitleaks.toml` keeps default rules and allows only the exact reviewed checksum values and that exact dummy value; no source directory or secret rule is broadly disabled. The reviewed scan returned zero findings. Final scans are recorded in the release report.

An independent exact-byte check searches for the actual private research password in every original shareable/evidence file and every publication file without printing it. The original private `.env` is expected to exist only in the research workspace. The clean package must contain no `.env`, private key, private log, database file, model weight, virtual environment or cache. Workstation-specific absolute paths are removed from publication documentation/report copies and those changes are recorded in `PUBLICATION.json`. Fictional attack paths in tests remain test inputs.

There is no Git history in this workspace to scan. Gitleaks directory scans do not establish the absence of secrets in future commits, external volumes or excluded private caches. Re-run a history scan after a repository exists and before any publication; do not copy the research `.env`.

## Static analysis

Bandit scanned the publication's `app` and `scripts`: 131 findings, zero scanner errors, zero high-severity findings and zero findings in runtime `app` code. Nine medium findings concern standard-library XML parsing in trusted offline JUnit/report scripts. The remaining 122 are low severity: 104 assert checks, six XML imports, five subprocess calls, three subprocess imports, three executable-path checks and one deterministic non-security random generator. Assertions are offline verification checks, not API authorization. Subprocess calls use fixed developer-controlled argument lists rather than document text. XML inputs must remain locally generated trusted test reports; do not feed downloaded or user-submitted XML into these tools. These findings are retained and triaged, not silently suppressed or called a clean static scan.

## Open dependency findings

`pip-audit` queried the PyPI advisory service for 56 installed distributions matching the Windows locked environment. It reported **nine advisory records in Transformers 4.57.6, representing six distinct advisory IDs**; three records are duplicates. This is an open audit finding, not a passed dependency-security gate:

| Advisory ID | Affected behavior reported by the scanner | Applicability to this runtime |
|---|---|---|
| PYSEC-2025-217 / CVE-2025-14929 | X-CLIP checkpoint conversion deserialization | This project does not convert X-CLIP checkpoints |
| PYSEC-2026-2288 / CVE-2026-1839 | Trainer RNG checkpoint loading with older PyTorch | No Trainer usage; installed Torch is 2.14.1, above the described pre-2.6 condition |
| PYSEC-2026-2289 / CVE-2026-4372 | Attacker-controlled model config/kernel loading | No caller-selected model/config; fixed pinned MiniLM cache only. `trust_remote_code=False` alone must not be treated as a universal mitigation |
| PYSEC-2026-2290 / CVE-2026-5241 | Nested LightGlue configuration trust bypass | LightGlue is not used |
| PYSEC-2026-3929 / CVE-2026-9856 | `save_pretrained` chat-template path traversal | The inference path does not save caller-provided tokenizers/processors |
| PYSEC-2026-4174 / CVE-2026-80047 | Custom generation module written before trust consent | No custom generation or generative model loading is used |

These applicability statements come from code inspection against the descriptions returned by the audit service, not exploit testing. Some advisory records lack a fix version; others point to Transformers 5.x, outside the frozen `<5` constraint. No major dependency migration was made during packaging. A separate migration must preserve historical results, recheck the pinned model behavior, rerun all tests/evaluation and rerun the audit. Do not load untrusted models, checkpoints, tokenizer configs or custom generation code with this environment. Do not present the dependency scan as zero vulnerabilities.

The advisory data is maintained in the [PyPA advisory database](https://github.com/pypa/advisory-database/tree/main/vulns/transformers); the model-config finding is also described in the [GitHub reviewed advisory](https://github.com/advisories/GHSA-29pf-2h5f-8g72). The publication retains a concise ID/version summary; the full raw audit output stays with the private verification evidence. To repeat the Windows environment scan after setup, run `uvx pip-audit --path .venv/Lib/site-packages --format json --output .local/dependency-audit.json`. Use `gitleaks dir . --redact` for secrets and `uvx --from bandit bandit -r app scripts` for static analysis. Findings are version- and date-specific and need a fresh review before publication.

Portfolio assessment is conditional on this narrowly scoped, trusted local model workflow and visible disclosure. Public service deployment, untrusted model support and a claim of production security fail the current gate. The owner must resolve or explicitly accept the dependency risk before publication; selecting a license and running hosted CI remain separate outstanding decisions. No security scan authorizes publishing the package.
