# Stage 3 report: real vector-only RAG baseline

Verified on **28 October 2026**, Asia/Calcutta. **Verdict: PASS.** Real local MiniLM embeddings, real Neo4j vector retrieval, a deterministic text answerer, the query API, repeatable evaluation, and required regression/integrity checks work. Stage 4 has not started.

This is a measured baseline, not a claim of strong multi-hop quality. At k=5, answer accuracy is 97.22% for one hop, 25% for two hops, and 4.17% for three hops. Missing retrieved intermediate evidence explains the answerable failures in this controlled dataset. No GraphRAG system has been evaluated, so no improvement is claimed.

## Files and implementation

**40 new files and 13 changed existing files**, with 143 shareable files in the project. See the complete [file inventory](../reports/stage3/FILE_MANIFEST.md). Local credentials, caches, environments, logs, and JUnit XML are excluded.

Main additions are `app/vector/`, the vector API router, offline baseline metrics, three test modules, migration 004, the synthetic text/gold datasets, CLI/index/evaluation/performance/verification scripts, five Stage 3 design/report documents plus the initial plan, and machine-readable evidence in `reports/stage3/`.

Existing files changed: `.env.example`, `README.md`, `pyproject.toml`, `uv.lock`, application configuration/lifespan, the database timeout interface, schema validation, schema/roadmap documentation, reports README, and the two legacy tests whose expected schema/API surface now includes Stage 3. Original migrations 001–003 and curated fixture payloads remain unchanged.

The source audit and short implementation plan were written before implementation in [STAGE3_PLAN.md](STAGE3_PLAN.md). Architecture, operating commands, metric definitions, and integrity details are in [architecture](VECTOR_BASELINE_ARCHITECTURE.md), [indexing](VECTOR_INDEXING.md), [evaluation](BASELINE_EVALUATION.md), and [integrity](BASELINE_INTEGRITY.md).

## Corpus, model, and index

| Item | Verified result |
| --- | --- |
| Indexed documents / canonical chunks | **92 / 92** |
| Existing Stage 1–2 corpus | 16 documents: 12 automatic snapshots of curated texts and 4 local TXT/Markdown sources |
| Benchmark extension | 76 explicitly synthetic text documents stored in a versioned JSON corpus |
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Pinned upstream revision | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| Inference | Actual Sentence Transformers, local CPU, two PyTorch threads, batches up to 32 |
| Vectors | 384 finite float components, L2 normalized; all 92 checked |
| Token window | 256 including special tokens; overlong text fails instead of being truncated |
| Database | Real Neo4j **5.26.32 Community** |
| Index | `chunk_minilm_cosine`, ONLINE, cosine, `ChunkEmbedding.embedding`, provider `vector-2.0` |
| Actual index defaults | Quantization enabled, HNSW m=16 and ef_construction=100; full schema in index evidence |
| Schema | 23 uniqueness constraints, 6 explicit range indexes, 1 vector index; 32 total indexes |

The initial public-weight download needs internet. Runtime inference is cache-only and offline. No paid providers, fabricated embeddings, Enterprise-only features, or hosted inference were used. The [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) and [Neo4j 5 vector documentation](https://neo4j.com/docs/cypher-manual/5/indexes/search-indexes/vector-indexes/) describe the underlying model/index capabilities; this report's quality and timing figures come from local runs.

Embeddings live in separate operational records referencing unchanged canonical chunk IDs. Document content, exact offsets, hashes, processing versions, ingestion ownership, original document references, and extraction properties are preserved. Indexing stages batches under a lease and publishes a complete versioned build atomically. Failures and stale builds cannot become current evidence. Repeating unchanged indexing returns the same build without duplicate chunks or vectors.

The active build is `vector-build:844933f2e03ad5f3ad8f1a7970d01c5bd342faf7`; embedding version is `embedding:d839a5883dc9e038153a627ffeac85de98ce1ad2`. Stage 2 processing version remains `processing:8d0ae79ff5fdbf8c4caefe1e67bef04ff8aea800`. [Index verification](../reports/stage3/index_verification.json) records all dimensions, schema, repeated-index checks, and **92 successful source provenance audits**.

## Vector-only integrity and generation

Retrieval uses only the Neo4j vector procedure and node metadata for current build/source/run validation. It does not traverse factual relationships, MENTIONS, or structural relationships. Corporate registry entries, curated fact records, and evaluation keys are absent from runtime imports. Ranking uses actual vector scores and a chunk-ID tie-break, without graph-based boosting.

The isolated integration database is a fresh disposable Community container without the development volume. Tests add false factual edges, alter them, remove all factual edges, and verify identical ordered retrieved chunks, scores, and answers. Another test captures actual executed queries and checks that vector search occurs without factual traversal. Static dependency checks enforce separation from evaluation/registry modules.

The generator is a deterministic grammar, **not an LLM**. It joins only explicit statements in retrieved chunk text, with scoped technology instances and exact qualified person names. It requires a complete source-supported path and cites every step. Source sentence boundaries/code context prevent clipped or fenced text becoming an assertion. Missing links, unsupported forms, contradictions, or unresolved names cause abstention. There is no graph fallback.

## Evaluation and quality

Dataset version `multihop-vector-v1` contains **122 labeled questions**: 36 one-hop, 36 two-hop, 24 three-hop, and 26 unanswerable. Each answerable case has a complete expected answer set, required source snapshots, exact-span supporting facts, and ordered reasoning chains used only for scoring. Calibration and held-out scenarios have separate names, question surfaces, and source layouts. Both were inspected during development, and share the same abstract relation grammar; these are synthetic controlled-domain results, not blind generalization estimates.

The headline configuration is **k=5**, sequential requests:

| Group | Questions | Answer exact-match | Required-fact coverage | Complete chain coverage | Abstention |
| --- | ---: | ---: | ---: | ---: | ---: |
| One hop | 36 | **97.22%** (35/36) | 97.22% | 97.22% | 2.78% |
| Two hops | 36 | **25.00%** (9/36) | 61.11% | 25.00% | 75.00% |
| Three hops | 24 | **4.17%** (1/24) | 35.42% | 4.17% | 95.83% |
| Unanswerable | 26 | **100%** correct null | Undefined | Undefined | **100%** |
| All answerable | 96 | **46.88%** (45/96) | **68.23%** | **46.88%** | **53.13%** |

Across all 122 questions, exact-match including correct unanswerable abstentions is 58.20%. Citation correctness is **100% (57/57)** at k=5. Unsupported answer count at k=5 is **zero**. A final-answer mention without all required intermediate facts does not receive complete-chain credit.

| k | Document Recall@k | Precision@k | Required-fact coverage | Complete chains / answerable accuracy | Unsupported answers |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 50.87% | 81.25% | 50.87% | 28.13% | **1** |
| 3 | 64.93% | 35.07% | 64.93% | 41.67% | 0 |
| 5 | 68.23% | 22.71% | 68.23% | 46.88% | 0 |
| 10 | 73.87% | 12.71% | 73.87% | 53.13% | 0 |

Retrieval and generation metrics are defined separately in the evaluation document. At k=5 all 45 complete-evidence cases were answered correctly under the supported grammar; 51 answerable cases abstained with missing retrieved support. This observation does not prove general language understanding. The k=1 unsupported result is an incomplete multi-project answer set: a returned branch had supporting text, but a second valid branch was absent. The strict evaluator counts that failure rather than treating a partial answer as complete.

Calibration one-/two-/three-hop accuracy at k=5 is 94.44% / 22.22% / 8.33%; held-out accuracy is 100% / 27.78% / 0%. These small, development-inspected splits do not justify an independent generalization claim. Full per-question results, actual scores, missed fact IDs, all hop/split/k groups, and timings are in [JSON](../reports/stage3/baseline_metrics.json), [CSV](../reports/stage3/baseline_metrics.csv), and [error analysis](../reports/stage3/error_analysis.md).

Two final real evaluations matched **all 488** ranked chunk lists, actual similarity scores, answers, citations counts, and quality measurements. Timings are expected to vary. [Repeatability evidence](../reports/stage3/reproducibility.json) records exactly which fields were compared.

## Controlled local performance

The recorded environment reports Windows 11, Python 3.12.13, AMD64 Family 23 Model 24, one available physical/logical CPU, and 14.90 GB RAM. Installed packages include Sentence Transformers 5.7.0, Transformers 4.57.6, CPU PyTorch 2.14.1, and Neo4j driver 6.4.1. Main evaluation uses concurrency 1, two inference threads, 92 chunks, and k=1/3/5/10. Timings below use the final k=5 run over 122 questions.

| Measurement | p50 | p95 |
| --- | ---: | ---: |
| Warm question embedding | **34.46 ms** | **76.85 ms** |
| Vector retrieval plus source/schema validation | **51.37 ms** | **138.28 ms** |
| End-to-end service response | **87.18 ms** | **217.92 ms** |

Fresh worker startup with already downloaded weights plus first inference took **15.79 seconds**; worker startup alone took 15.39 seconds. This is process-cold, not a forced cold operating-system file cache. The initial uncontrolled import after dependency setup took about 94 seconds amid WSL recovery, so default startup allows 180 seconds. Downloads and HTTP network/serialization overhead are excluded from the service latency timer.

Warm batched indexing processed 92 chunks in **5.67 seconds**, or **16.23 chunks/second**, including canonical reads, real inference, writes, and publication validation. An unchanged repeat created no duplicates. A separate fixed Atlas-query benchmark measured 24 requests each at concurrency 1 and 4; end-to-end p50/p95 were 83.28/232.13 ms and 416.52/644.49 ms respectively. This reflects local CPU/queue contention and is not a production throughput claim. Final parent RSS was 82.8 MB and model-worker RSS 487.2 MB. Full measurements are in [performance evidence](../reports/stage3/performance.json) and the evaluation JSON.

## Tests, API startup, and actual outage recovery

Final full suite: **241 passed, 0 failed, 0 errors, 0 skipped**, in **211.69 seconds**. This comprises **184 unit tests and 57 real integration tests**, including all 180 Stage 1–2 cases. Exact case/status inventory is in [test results](../reports/stage3/test_results.json). Ruff lint, formatting checks, and locked dependency validation pass.

Real tests cover cached model inference, missing weights, invalid/non-finite vectors, token limits, ONLINE/missing index, source corruption, removed chunks, stale source/model versions, unchanged indexing, failed real write rollback, incomplete publication, expired/concurrent writer claims, publication/query races, concurrent real API requests, unused Bolt endpoint failure/recovery, graph-edge independence, and previous functionality. Integration tests were run explicitly and not silently skipped.

`POST /api/v1/rag/vector/query` returns measured scored chunks, validated provenance, supported answers/citations or explicit abstention. Input bounds and extra-field rejection return 422. Dependency errors return safe 503 responses, not fabricated answers or successful abstentions. No arbitrary Cypher endpoint exists.

[Runtime verification](../reports/stage3/runtime_verification.json) used a real temporary Uvicorn process and actual HTTP calls:

| State | Health | Readiness | Vector query |
| --- | ---: | ---: | --- |
| Connected | 200 | 200 | 200, PostgreSQL answer with exact source citation |
| This project's Neo4j stopped | 200 | 503 | **503**, safe database error, no answer field |
| Fresh API starts during outage | 200 | 503 | Process starts without database/model preloading |
| Neo4j restored | 200 | 200 | 200, PostgreSQL answer and valid evidence again |

Six concurrent real HTTP requests passed, invalid input returned 422, and request IDs were checked. The script restored Neo4j and stopped its temporary API process. The original curated graph remains exactly **50 nodes, 91 relationships, 30 facts**, with all expected evidence paths. All 92 indexed sources passed the Stage 2 provenance audit.

## Problems resolved and limits

Docker initially failed with WSL CreateVm/AttachDisk timeouts. A WSL shutdown, Docker restart, and user-assisted engine recovery restored the existing volume. No data reset or unrelated project changes were used. Neo4j reports its configured cosine function as uppercase `COSINE`; schema checking now accepts that normalized representation. Cold vector-query compilation exceeded the old five-second read timeout, so vector operations have a separate bounded 20-second deadline while ordinary readiness retains five seconds. A final publication recheck closes the query/rebuild race.

The corpus and labels are synthetic and small. The deterministic grammar and lexical identity handling are narrow. The model rejects chunks above 256 tokens; it does not silently truncate or invent replacement vectors. Source freshness depends on explicit Stage 2 refreshes, with no filesystem watcher. Historical/incomplete builds are retained and require eligibility gates.

Neo4j 5.26 lacks metadata prefiltering in its vector procedure. This baseline requests all physical vector candidates up to a 10,000-record limit, then filters current metadata before taking k. Ranking remains exclusively vector-based, but this strategy is unsuitable for claiming large-scale efficiency. Approximate index behavior, quantization, OS caches, local contention, and the tiny benchmark limit broader conclusions.

The benchmark extension uses names outside Stage 2's reviewed registry. Original text is available to the baseline even where automatic graph extraction rejected unfamiliar identities. A future graph experiment must measure extraction coverage on the same frozen corpus and must not load evaluation gold into runtime. These low multi-hop baseline scores do not establish that GraphRAG will outperform it.

## Reproduction

Run from `D:\Projects\GraphRAG-MultiHop` in PowerShell, after the README prerequisites:

```powershell
uv sync --locked
docker compose --progress plain up -d --wait
uv run python -m scripts.graph migrate
uv run python -m scripts.graph load
uv run python -m scripts.vector prepare-model
uv run python -m scripts.vector index
uv run python -m scripts.vector index
uv run python -m scripts.vector status
uv run python -m scripts.vector query --question 'Which database does Project Atlas use?' --top-k 5
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run pytest --run-integration -q -x --tb=short --junitxml=reports/stage3-tests.xml
uv run python -m scripts.verify_vector_index
uv run python -m scripts.evaluate_baseline
uv run python -m scripts.benchmark_vector
uv run python -m scripts.verify_vector_runtime
uv run python -m scripts.serve
```

Run outage verification sequentially after database tests and measurements. To reproduce the two-run comparison, copy the first metrics JSON to `.pytest_cache/stage3-final-first-evaluation.json`, run evaluation again, then run `uv run python -m scripts.verify_baseline_repeat`. Keep the corpus/model versions fixed; timings need not match.

**Stage 3 PASS.** No paid calls, Git commit/push, new repository, deployment, or Stage 4 work occurred.
