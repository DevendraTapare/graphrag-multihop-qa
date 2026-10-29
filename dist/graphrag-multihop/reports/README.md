# Verification evidence

Stage 5 evidence is in `stage5/`:

- `history_freeze.json`, `frozen_stage4.zip`: all 187 shareable Stage 1–4 files, nonsecret configuration and original graph hash.
- `coverage_audit.json`: exact vector/graph source sets, 64-label support, resolvable starts, rejections, historical exclusions and every question's before/after coverage.
- `build_manifest.json`, `backfill_verification.json`, `index_verification.json`: source-only construction, two identical ingestion passes and repeated real vector indexing.
- `identity_audit.json`, `provenance_audit.json`, `aligned_snapshot.json`: stored identities, all 150 source proofs and isolated graph state.
- `runtime_freeze.json`: final retrieval/source-manifest hashes before final scoring. `runtime_freeze_initial.json` and `development_evaluation_summary.json` preserve the earlier completeness-review record.
- `vector_aligned_metrics.json`, `graph_aligned_metrics.json`, `hybrid_metrics.json`: full three-mode measurements, source versions, environment, splits, hops, tags and every response.
- `hybrid_no_expansion_metrics.json`, `hybrid_no_reranking_metrics.json`, `ablation_results.csv`: component effects, including negative/null results.
- `comparison.json`, `error_analysis.md`, `performance.json`: frozen-versus-new results, all failed/abstained cases and separate model startup/first-request conditions.
- `runtime_verification.json`: all three real HTTP modes, concurrent IDs/timings, isolated Compose outage/restart/recovery with historical readiness preserved.
- `determinism.json`, `test_results.json`, `FILE_MANIFEST.md`: repeated equality, full regression evidence and exact changed/new file inventory.
- `../docs/STAGE5_REPORT.md`: measured outcome and limits.

Stage 4 evidence is in `stage4/`:

- `baseline_freeze.json`, `frozen_stage3.zip`, `graph_snapshot.json`: exact pre-change code/configuration, historical results, and real graph state.
- `retrieval_code_freeze.json`: graph runtime hashes fixed before the primary benchmark.
- `graph_metrics.json` and `.csv`: same 122 questions, hop/split/tag/plan metrics, identities, phase latency, every failed/abstained example.
- `error_analysis.md`: all abstentions with failure causes and upstream origins.
- `source_coverage.json`: all 64 gold facts audited against the frozen graph; none has accepted support.
- `operational_verification.json`: 68 current assertion proofs, real original-domain responses, warm active workloads and exact repeated paths/citations.
- `vector_recheck.json`, `comparison.json`: read-only unchanged k=5 vector replay, exact quality/chunk equality and new timings alongside frozen results.
- `runtime_verification.json`: real graph HTTP requests, concurrent IDs, API startup, Compose outage/restart/recovery.
- `test_results.json`, `determinism.json`: complete zero-skip suite and repeated benchmark equality.
- `FILE_MANIFEST.md`: Stage 4 additions and changes to existing files.
- `../docs/STAGE4_REPORT.md`: outcome, measurements and limitations.

Stage 3 evidence is in `stage3/`:

- `baseline_metrics.json` and `.csv`: real MiniLM/Neo4j results by k, hop, split, and individual question.
- `error_analysis.md`: missing evidence and generation failures at k=5.
- `performance.json`: controlled warm batch indexing, repeated indexing, and concurrency measurements.
- `runtime_verification.json`: actual HTTP startup, vector requests, Compose outage, and recovery.
- `test_results.json`: complete regression/integration test statuses and counts.
- `index_verification.json`: actual index schema, dimensions, source count, idempotency, and Stage 1–2 preservation.
- `FILE_MANIFEST.md`: Stage 3 additions and changed existing files.
- `../docs/STAGE3_REPORT.md`: measured outcome and limitations.

Stage 2 evidence:

- `stage2-test-results.json`: final full regression suite, including real Neo4j cases.
- `stage2-corpus-verification.json`: 16-document import, repeated-load equality, source audits, and Stage 1 preservation.
- `extraction-evaluation.json`: calibration, held-out, combined, and per-case synthetic extraction measurements.
- `stage2-runtime-verification.json`: real database outage/recovery and ingestion results.
- `stage2-cli-verification.json`: successful summary, validation, rejection/conflict inspection, and history listing.
- `STAGE2_FILE_MANIFEST.md`: current shareable inventory and changed Stage 1 files.
- `../docs/STAGE2_REPORT.md`: complete Stage 2 report and limitations.

Historical Stage 1 evidence:

- `test-results.json`: all 78 cases from the final successful JUnit report, including 18 real Neo4j integration cases. No cases were skipped.
- `graph-validation.json`: live graph counts and the verified Priya evidence paths.
- `runtime-verification.json`: real process startup and database outage/recovery HTTP results.
- `FILE_MANIFEST.md`: shareable project files created in Stage 1.
- `../docs/STAGE1_REPORT.md`: the complete report and limitations.

Ignored local artifacts include `.log` files, JUnit `.xml` files, and `runtime-api-process.json`. The latter records the PID of the local review API started during implementation. To stop that process in the same Windows session:

```powershell
$reviewApi = Get-Content reports/runtime-api-process.json | ConvertFrom-Json
Get-CimInstance Win32_Process -Filter "ProcessId = $($reviewApi.pid)" |
    Where-Object { $_.CommandLine -like '*-m scripts.serve*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId }
```

The command checks the process command line before stopping it because Windows can reuse process IDs. Neo4j can be stopped separately with `docker compose stop neo4j`. To run the API again in the foreground, use `uv run python -m scripts.serve` and stop it with Ctrl+C.
