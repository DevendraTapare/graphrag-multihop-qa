# Stage 4 report — graph-based multi-hop retrieval

Stage 4 implements a graph-only question-answering pipeline over real Neo4j paths. It resolves reviewed identities, follows approved one-/two-/three-hop factual sequences, validates every edge's source proof, and returns deterministic answers with machine-readable paths and citations. Ambiguous, conflicting, unsupported, stale, or incomplete evidence causes abstention. It uses no model, paid API, vector fallback, runtime answer key, or new fabricated fact.

**Verdict: PASS for the Stage 4 implementation and verification criteria. Graph-only benchmark coverage is poor: 0% answerable accuracy, with no improvement over the vector baseline.** There is no required accuracy-improvement threshold in Stage 4; these results are reported without repairing the frozen graph using evaluation labels. Stage 5 has not started.

## Delivered files and behavior

New runtime code is in `app/graph_rag/` and `app/api/graph_rag.py`. It includes strict typed plans, a finite versioned grammar, exact type-aware registry linking, bounded parameterized Neo4j templates, independent curated/automatic source proof, deterministic path grouping/selection, and answer generation. The endpoint is `POST /api/v1/rag/graph/query`. `scripts.graph_rag` provides plan/link/query commands.

New offline grading is in `app/evaluation/graph.py`. New scripts freeze-check and evaluate the graph, audit missing source coverage, replay unchanged vector retrieval, verify every current fact, measure active graph workloads, exercise live HTTP outage/recovery, and record full-suite/determinism evidence. Four new test modules cover graph runtime, API, evaluation normalization, and real adversarial database cases.

The only changed pre-existing files are `.env.example`, `app/core/config.py`, `app/main.py`, `tests/unit/test_api.py`, `README.md`, `docs/PROJECT_ROADMAP.md`, and `reports/README.md`. Changes add graph settings/API integration and documentation. Dependencies, migrations, registry, extraction, vector runtime, datasets, baseline grading, and Stage 1–3 reports remain unchanged. The complete inventory is [FILE_MANIFEST.md](../reports/stage4/FILE_MANIFEST.md).

Read [architecture](GRAPH_RETRIEVAL_ARCHITECTURE.md), [entity linking](ENTITY_LINKING.md), [reasoning/provenance](MULTIHOP_REASONING.md), [evaluation](GRAPH_EVALUATION.md), and [security tests](GRAPH_SECURITY_TESTS.md). The pre-implementation audit and plan are in [STAGE4_PLAN.md](STAGE4_PLAN.md).

## Baseline preservation

Before modifying existing files, Stage 4 hashed and archived 143 shareable Stage 3 files, exact nonsecret settings, dataset/model/build identities, historical metrics, and the real graph snapshot. Files are under `reports/stage4/`: `baseline_freeze.json`, `frozen_stage3.zip`, and `graph_snapshot.json`. Graph runtime hashes were frozen separately before primary evaluation; there was no held-out retrieval tuning.

The graph snapshot hash remains `449ea1c1703fcecf7a75f2445102d9de19a5b7c8624fd41985675ce154a57a63`: 254 GraphNodes, 622 relationships, 93 source records, 110 runs, 92 embedding records. The original fixture remains 50 nodes, 91 relationships, and 30 facts; automatic current facts remain 38. Source selection uses the frozen 92-source manifest, not the vector index. No schema migration was needed.

## Measured benchmark outcome

The same `multihop-vector-v1` dataset, source snapshot and unchanged Stage 3 grading rules were used. The 122 questions comprise 96 answerable and 26 unanswerable cases. Calibration and held-out splits each have 48 answerable and 13 unanswerable cases. All answerable results below are zero in both splits. Full rows, hop/tag/plan breakdowns and every abstention are preserved in `graph_metrics.json`, `graph_metrics.csv`, and `error_analysis.md`.

| Measure | Graph-only | Frozen vector-only, k=5 |
| --- | ---: | ---: |
| One-hop accuracy | 0/36 = 0% | 35/36 = 97.22% |
| Two-hop accuracy | 0/36 = 0% | 9/36 = 25.00% |
| Three-hop accuracy | 0/24 = 0% | 1/24 = 4.17% |
| Answerable exact accuracy | 0/96 = 0% | 45/96 = 46.88% |
| Overall exact accuracy, including correct abstentions | 26/122 = 21.31% | 71/122 = 58.20% |
| Required-evidence recall | 0% | 68.23% |
| Complete textual chain coverage | 0% | 46.88% |
| Validated Neo4j chain coverage | 0% | N/A |
| Citation correctness | N/A: zero citations | 57/57 = 100% |
| Answerable abstention | 96/96 = 100% | 51/96 = 53.13% |
| Correct unanswerable abstention | 26/26 = 100% | 26/26 = 100% |
| Unsupported answers | 0 | 0 |

The graph grammar supports all 122 questions, but the unchanged registry lacks every answerable starting identity. Resolution returns 121 not_found and one ambiguous, with zero canonical assignments and zero wrong assignments. Assignment accuracy is N/A, not 100%. Lee Chen ambiguity is detected; unregistered Jordan Vale is not identified as ambiguous. Intended ambiguous-person detection is 1/2; both cases safely abstain. No benchmark request traverses an edge, so provenance failure rate is also N/A, not a perfect score.

The independent offline coverage audit finds zero accepted graph matches for all 64 gold facts. The new benchmark documents introduced names outside the reviewed Stage 2 registry. This is an upstream extraction/identity coverage limitation. Vector retrieval can read their original text, while graph retrieval cannot invent their identities or missing edges. The 96 answerable failures therefore originate before Stage 4 traversal. The other 25 not_found results are correct abstentions on intentionally missing/unregistered cases, plus one correct explicit ambiguity abstention. `source_coverage.json` records this audit; no gold-derived graph insertions were made.

For fair grading, offline source normalization maps curated document IDs to existing automatic copies only when original content hashes match, preserves exact source spans/text, and collapses duplicate original source copies. Runtime source IDs and assertion attribution remain intact. The unchanged baseline chain measure checks textual evidence; a separate measure requires actual validated graph-path steps. Details and normalization tests are in [GRAPH_EVALUATION.md](GRAPH_EVALUATION.md).

## Working paths and provenance

Original-domain verification is separate from benchmark scoring. Actual queries resolve Morgan → Atlas East; Atlas → PostgreSQL; qualified Priya → Atlas → PostgreSQL → AWS; Comet → manager → Cedar Kite; Delta → Tidal Lantern; and Atlas East → its PostgreSQL instance → Azure. Every factual type is exercised. Plain Priya and Lee Chen remain ambiguous. Ivo's unrecorded employment causes abstention. Beacon hosting has conflicting supported AWS/GCP assertions: singular questions abstain and retain both paths; plural questions return both answers.

The qualified Priya three-hop response groups one logical path with nine actual supporting assertion citations. It inspects 39 raw prefix/full candidates, including combinations of parallel supports. These are not 39 different logical chains. Full responses and native paths are in `operational_verification.json`.

An independent audit validates all 68 current factual assertions: 30 curated and 38 automatic, with zero provenance failures and 68/68 exact source-grounded citations. This is a full-current-fact audit, not a benchmark citation score. Curated and automatic copies of one original document count as separate assertions, not independent original sources. Real isolated tests prove that one failed source cannot erase a different valid source's support.

## Performance

The recorded environment is Windows 11, Python 3.12.13, Neo4j Community 5.26.32, one physical/logical CPU, and approximately 14.9 GB host RAM. The same local database/corpus and locked dependencies were used. Query plans and pages are warm for active-query timings; first examples are retained separately. Graph work needs no embedding-model startup. Vector replay loads cached local model weights in a new worker; startup plus first inference took 16.11 seconds and is excluded from warm quantiles.

| Workload | p50 / p95, milliseconds |
| --- | ---: |
| Frozen vector retrieval, k=5 | 51.37 / 138.28 |
| Frozen vector end-to-end, k=5 | 87.18 / 217.92 |
| New unchanged vector replay retrieval, k=5 | 86.02 / 219.26 |
| New unchanged vector replay end-to-end, k=5 | 133.20 / 349.56 |
| Graph benchmark, repeated run, early abstention only | 0.05 / 0.36 |
| Active graph parsing, concurrency 1 | 0.06 / 0.08 |
| Active graph linking, concurrency 1 | 0.01 / 0.02 |
| Active graph traversal, concurrency 1 | 37.44 / 217.15 |
| Active graph provenance, concurrency 1 | 40.47 / 72.97 |
| Active graph revalidation, concurrency 1 | 74.99 / 225.56 |
| Active graph end-to-end, concurrency 1 | 181.58 / 509.72 |
| Active graph end-to-end, concurrency 4 | 557.67 / 1022.87 |

Each active workload contains seven supported original-domain questions repeated five times: 35 requests, 360 total raw candidates, and zero discarded paths. Answers, paths, sources and citations match across all repeats at concurrency one and four. First examples include query-plan compilation and reach 3.70 seconds. The recovered three-hop HTTP request after a database restart took 17.63 seconds, within the twenty-second request budget; this cold behavior is materially slower than the warm workload.

The primary graph benchmark's sub-millisecond latency measures no database work and demonstrates no traversal speed advantage. Active graph and vector benchmark questions differ, so their timings are not a controlled retrieval speed comparison. The unchanged vector replay reproduces all compared answers, quality scores, citations and ranked chunk IDs exactly. Historical results are not overwritten. See `comparison.json` and `vector_recheck.json`.

## Final verification

The final complete suite contains **354 passing tests: 253 unit and 101 real integration, zero skipped, zero failed, zero errors**. This includes all 241 Stage 1–3 cases and 113 new Stage 4 cases (69 unit, 44 real graph integration). Ruff lint, Ruff formatting, and the locked dependency check pass. Required graph adversarial scenarios execute against real isolated Neo4j, including wrong directions, nearby unrelated nodes, cycles, unsupported shortcuts, incomplete branches, source deletion/corruption/staleness/failure, conflicts, source correction, independent support, candidate/answer bounds, vector-index removal, source-change revalidation, outages and concurrent requests. See `test_results.json` and the local JUnit `reports/stage4-tests.xml`.

The real HTTP exercise starts Uvicorn on an ephemeral loopback port, verifies health/readiness, answers the three-hop query, serves eight concurrent requests with eight distinct IDs, rejects excessive depth with 422, stops Compose Neo4j, verifies health=200/readiness=503 and safe query 503, restarts the API during the outage, restores Neo4j, and answers again. Startup to health took 4.11 seconds. The temporary API process is stopped and Neo4j remains running. The database volume and graph snapshot are preserved.

Two complete 122-question graph evaluations match every non-timing per-question result. Runtime hashes remain identical to the pre-evaluation freeze. Active traversal repeats also match complete paths/citations. Final baseline hash/settings and graph snapshot checks pass. Evidence is in `determinism.json`, `runtime_verification.json`, and `test_results.json`.

To reproduce the checks in PowerShell:

```powershell
Set-Location <research-workspace>
docker compose --progress plain up -d --wait neo4j
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run pytest --run-integration -q --tb=short --junitxml=reports/stage4-tests.xml
uv run python -m scripts.evaluate_graph
Copy-Item -LiteralPath reports/stage4/graph_metrics.json -Destination .pytest_cache/stage4-first-graph.json
uv run python -m scripts.evaluate_graph
uv run python -m scripts.audit_graph_coverage
uv run python -m scripts.verify_graph
uv run python -m scripts.compare_stage4
# Run sequentially after database tests; this temporarily stops Neo4j.
uv run python -m scripts.verify_graph_runtime
uv run python -m scripts.record_stage4
```

## Remaining limits

The finite grammar and frozen reviewed registry constrain recall. The benchmark's missing identities/facts prevent useful graph answers. Source proof establishes support in controlled fictional text, not external truth. Candidate, answer, source-size and time limits can cause conservative abstention. Revalidation spans multiple reads and does not create an atomic snapshot through HTTP delivery. Cold query compilation can approach the request budget on this machine. The local API has no production authentication, global admission control, or broad load testing. No general LLM understanding, hybrid retrieval, deployment, GitHub repository, commit, push, or Stage 5 work was introduced.
