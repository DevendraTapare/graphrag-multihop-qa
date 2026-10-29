# Baseline integrity and reliability

Vector-only means the candidate documents and their order come exclusively from MiniLM question/chunk embeddings and Neo4j vector scores. Node metadata validates provenance and publication. The deterministic generator may join explicit statements inside the returned text, but cannot fetch additional evidence or consult the stored knowledge graph.

The integrity suite combines static dependency checks, captured executed queries, and a real destructive experiment in a separate disposable Neo4j Community container. The development database/volume is never used for edge-removal experiments.

| Check | Evidence |
| --- | --- |
| Real inference | Cached Sentence Transformers model, 384 finite normalized components, repeatability and token-limit rejection |
| Real index | Actual migration and ONLINE schema inspection in Neo4j 5.26 Community |
| Edge independence | Retrieve/answer, create false factual edges, alter factual edges, remove factual edges in isolated container; ordered chunk IDs, scores, and answers remain identical |
| Query independence | Record actual runtime queries; prohibit factual types, MENTIONS, and relationship patterns; require vector query procedure |
| No gold/registry imports | Parse runtime imports and prohibit evaluation, registry, fixture-answer and graph-query modules/data |
| Complete support | Remove each intermediate text chunk and require abstention; final-answer mention alone does not count as full evidence |
| Publication/version safety | Change a source, omit an intermediate, remove a canonical chunk, corrupt a source, and reject/exclude invalid evidence |
| Transaction safety | Raise after a real batch write, verify rollback and failed publication, then retry successfully |
| Dependency errors | Missing model cache, missing vector index, invalid vectors, unused Bolt endpoint, real Compose outage and recovery produce explicit errors |
| Concurrent behavior | Shared real worker and connection pool process simultaneous requests consistently |
| Regression preservation | Run every Stage 1–2 test and validate unchanged curated namespace and automatic provenance |

The isolated database uses the same pinned image as development with fresh random credentials passed through a child environment. The fixture removes only its own uniquely named container afterward and mounts no development data volume. There is no destructive edge experiment in the shared database. Tests marked integration require `--run-integration`; required verification uses that flag so failures cannot become silent skips.

```powershell
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run pytest --run-integration -q --junitxml=reports/stage3-tests.xml
uv run python -m scripts.graph validate
uv run python -m scripts.verify_ingestion
uv run python -m scripts.evaluate_extraction
uv run python -m scripts.verify_vector_runtime
```

Run outage verification sequentially after all database tests/evaluations. It stops only this Compose project's Neo4j service, verifies a real HTTP vector request returns 503 during the outage, restores the service, and verifies successful vector evidence again. Health remains 200. Readiness retains its database-connectivity semantics. Errors contain safe categories/request IDs, not raw driver/model exceptions or invented answers.

Tests and schema guards prove the implemented paths under measured local conditions. They do not protect against an administrator rewriting both metadata and source snapshots, prove general semantic entailment, or establish production scalability. Corpus freshness is bounded by explicit Stage 2 refreshes. See the indexing and evaluation documents for those limits and for the 5.26 candidate filtering strategy.
