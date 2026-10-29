# Graph-only evaluation

The graph pipeline answers none of the frozen benchmark's 96 answerable questions. This is a measured failure of end-to-end coverage, not an improvement over vector retrieval. It correctly abstains on all 26 unanswerable cases and produces no unsupported answer. Working original-domain paths are verified separately and never added to benchmark accuracy.

## Frozen comparison

Before changing existing files, Stage 4 archived 143 shareable Stage 3 files and recorded their SHA-256 hashes, exact nonsecret settings, model revision, vector build, dataset version, and graph snapshot. `baseline_freeze.json`, `frozen_stage3.zip`, and `graph_snapshot.json` preserve this state. Stage 3 data, registry, extraction, grader, vector runtime, reports, dependencies, and migrations remain unchanged. The seven permitted integration files are API wiring/settings, example environment, README/roadmap/report index, and the expected API route list. The graph parser/runtime was separately hashed before the primary benchmark in `retrieval_code_freeze.json`.

The dataset is `multihop-vector-v1`: 122 synthetic questions, including 36 one-hop, 36 two-hop, 24 three-hop, and 26 unanswerable questions. Calibration and held-out splits each contain 61 questions (48 answerable, 13 unanswerable). Both splits have zero graph accuracy on answerable questions. Graph-only runs use max_hops=3, 128 total raw candidates, ten answer identities, ten-second query and twenty-second request budgets. The frozen vector comparison uses top_k=5 and the same source corpus. Neither runtime receives gold labels.

The graph snapshot contains 254 GraphNodes, 622 relationships, 93 source records, 110 ingestion runs and 92 embedding records. Only the approved 92 automatic source IDs, current ready publication, current processing version, and original curated fixture are eligible. Snapshot checks before/after evaluation, vector replay, operational checks, outage/recovery, and final verification compare the same full payload hash:

`449ea1c1703fcecf7a75f2445102d9de19a5b7c8624fd41985675ce154a57a63`

## Quality

| Metric | Frozen vector-only, k=5 | Graph-only |
| --- | ---: | ---: |
| One-hop exact answer | 35/36 = 97.22% | 0/36 = 0% |
| Two-hop exact answer | 9/36 = 25.00% | 0/36 = 0% |
| Three-hop exact answer | 1/24 = 4.17% | 0/24 = 0% |
| Answerable exact answer | 45/96 = 46.88% | 0/96 = 0% |
| All-question exact answer, including correct abstentions | 71/122 = 58.20% | 26/122 = 21.31% |
| Required-evidence recall | 68.23% | 0% |
| Complete textual evidence-chain coverage | 46.88% | 0% |
| Validated graph-chain coverage | Not a vector metric | 0% |
| Answerable abstention | 51/96 = 53.13% | 96/96 = 100% |
| Correct unanswerable abstention | 26/26 = 100% | 26/26 = 100% |
| Citation correctness | 57/57 = 100% | N/A: zero citations |
| Unsupported answer count | 0 | 0 |

The unchanged `app/evaluation/baseline.py` grades exact answers, required original source spans, retrieved-document recall, textual chain coverage, citations, abstentions, and unsupported answers. Graph phase timing and identity/provenance diagnostics are additional metrics in `app/evaluation/graph.py`. JSON includes results by split, hop, question tag, parser rule, and every individual question. CSV provides the main per-question measures; `error_analysis.md` preserves all 122 abstentions with expected/actual results and failure origins.

### Source representation normalization

Graph citations expose native curated or automatic document/chunk IDs. The frozen vector corpus contains automatic source snapshots, including copies of the twelve curated documents. Offline normalization maps a curated document ID to that existing automatic snapshot only when the verified original content hash matches. It preserves exact Unicode offsets and text. Identical normalized document/span/text chunks are collapsed, and citations use the corresponding selected chunk ID; identical document/span/quote citations are collapsed. Native runtime responses retain every assertion and source-kind attribution. Duplicating a curated document through automatic ingestion does not create another independent original source.

The unchanged baseline chain metric checks whether retrieved text contains all required spans; it does not require Neo4j edges. Stage 4 also records `validated_graph_chain_coverage`, requiring actual returned full-path steps and exact supporting fact spans. Text coverage is never presented as graph proof. N/A denominators remain JSON null, including citation correctness and provenance failure rate when the benchmark traverses no edges.

## Why graph accuracy is zero

The 76 Stage 3 extension documents contain the benchmark's new fictional names. Those identities were not added to Stage 2's reviewed registry, so their intended relationships were never accepted into the graph. `source_coverage.json` independently compares all 64 gold facts to the frozen registry and actual stored assertions: zero have matching graph support. All 96 answerable question starts are outside the registry. The text-only vector baseline can still read these documents.

Every benchmark question parses into a supported plan. Resolution returns 121 not_found and one ambiguous. There are zero resolved assignments and zero wrong assignments; assignment accuracy is N/A. Of two deliberately ambiguous-person cases, Lee Chen is correctly detected as ambiguous; unregistered Jordan Vale returns not_found. The system safely abstains in both cases, but ambiguity-detection coverage is only 1/2.

The 96 answerable failures are classified as missing extraction facts / Stage 2 identity coverage. The other 25 not_found cases are expected missing or unregistered entities on unanswerable questions, rather than 25 additional extraction defects. The remaining abstention is explicit registry ambiguity. No benchmark query reaches traversal or provenance; candidate count, discarded paths, and checked edges are zero. These zeros establish neither perfect provenance nor high-recall linking.

For example, `s01-q01` asks which project Asha Rao manages. Its grammar is supported, but Asha Rao has no reviewed canonical identity. The runtime returns `entity_not_found` without looking up the expected answer. Expanding the registry or inserting missing facts using benchmark labels would alter the frozen experiment and was not done. The original qualified Priya chain works; that demonstration does not repair benchmark coverage.

## Performance and reproducibility

All measurements use the same local Windows 11 machine and pinned Neo4j Community 5.26.32. Recorded hardware is one physical/logical CPU and approximately 14.9 GB host RAM; Docker has its own configured memory limit. Exact OS, CPU, Python version, registry/processing identity, graph limits, and runtime hashes are in `graph_metrics.json`. No paid calls or network model inference are involved.

The frozen vector p50/p95 is 51.37/138.28 ms for retrieval and 87.18/217.92 ms end-to-end. Stage 4's new vector replay uses unchanged runtime/model/build/grader at k=5; `vector_recheck.json` records new warm timings and compares answers, chain measures, citations, unsupported counts and retrieved chunk IDs against the frozen results. Cached local model weights are loaded in a new worker, with startup recorded separately. Its measurements run sequentially with graph workloads.

Graph benchmark timing is an early-abstention workload: parsing and registry lookup only, with no Neo4j traversal. Its sub-millisecond timings must not be used to claim a retrieval speed advantage. The first and repeated full benchmark timing distributions are retained in `determinism.json`; the latest primary measurements are in `graph_metrics.json`.

`operational_verification.json` measures actual answered graph queries over seven original-domain cases, five repetitions each, separately at concurrency one and four. The source audit and first examples warm database plans/pages before measurement. At concurrency one, p50/p95 is 181.58/509.72 ms end-to-end, 37.44/217.15 ms traversal, 40.47/72.97 ms provenance, and 74.99/225.56 ms revalidation. At concurrency four, end-to-end is 557.67/1022.87 ms. Each workload has 35 requests, 360 total raw prefix/full candidates, and zero paths discarded. Raw candidate counts include parallel supporting assertions; they are not distinct logical chains. Individual first examples include query-plan compilation and reach 3.70 seconds; they are not fully cold database restarts. These are different questions from the benchmark and cannot support a controlled speed comparison with vector retrieval.

The separate full-fact audit verifies 68/68 current factual assertions (30 curated, 38 automatic), exact source text/spans and endpoint identities, with zero provenance failures. This gives 100% source-grounding correctness on that audit, not a 100% benchmark citation score. All supported operational responses, paths, citations, conflicts and abstentions are preserved. Five repeated active workloads at concurrency one/four must match every non-timing response field. Two full 122-question runs must also match every non-timing per-question result. Final verification checks file hashes and the graph snapshot again.

```powershell
# Requires the existing frozen source corpus and running Neo4j.
uv run python -m scripts.evaluate_graph
uv run python -m scripts.audit_graph_coverage
uv run python -m scripts.verify_graph
uv run python -m scripts.compare_stage4
# Real outage check: run after other DB work; it restores Neo4j.
uv run python -m scripts.verify_graph_runtime
```

Limits remain the finite grammar, reviewed identity coverage, missing extracted benchmark facts, small synthetic corpus, bounded local workload, and non-atomic final revalidation. Graph correctness on supported original-domain facts does not imply useful benchmark coverage. The current graph-only pipeline does not outperform vector-only RAG.
