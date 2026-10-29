# Stage 1 report

Verification date: **28 October 2026**, Asia/Calcutta.

**Verdict: PASS.** The local API runs, the real Neo4j Community database connects, migrations and fixtures are loaded, sourced two-hop and three-hop paths exist, and readiness detects an actual outage and recovery. Stage 2 has not started.

## 1. Files created

The complete shareable file inventory is in [FILE_MANIFEST.md](../reports/FILE_MANIFEST.md). Main deliverables are:

- `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `.env.example`, and `compose.yaml`.
- Application packages for API routes, configuration, logging, database access, migrations, graph contracts, fixtures, loading, and validation.
- Two versioned Cypher migrations.
- A JSON corpus containing 12 fictional documents and their evidence-backed graph, plus nine evaluation cases.
- Scripts for local credentials, corpus generation, schema migration, fixture load/validation/reset, server startup, and real outage/recovery verification.
- Separate unit and real Neo4j integration tests.
- README, architecture, schema, provenance, roadmap, infrastructure notes, and verification artifacts.

The local `.env`, virtual environment, caches, logs, and JUnit XML are ignored development artifacts. No real credentials are included in shareable files. No GitHub repository, commit, push, or deployment was created.

## 2. Architecture implemented

FastAPI uses an application factory and lifespan-managed official Neo4j driver. The driver has a connection pool, configured database, bounded connection/acquisition/query timeouts, and explicit cleanup. Database connectivity is lazy so the API can start during an outage.

`/health` and `/ready` also exist under `/api/v1`. Health checks the process. Readiness executes a real query against the selected database. Request IDs correlate responses with JSON application logs. Error handlers return safe messages without credentials or raw request inputs. Internal queries use parameters; there is no Cypher execution API.

Fixture imports use a bounded atomic transaction, stable IDs, required uniqueness constraints, a per-fixture write lock, and complete snapshot collision checks. Reset requires development mode and an explicit fixture-ID confirmation, refuses external edges, and preserves unrelated data.

## 3. Database schema

Domain labels: Person, Organization, Project, Technology, Platform, Document, and Chunk. Every domain node also has `GraphNode` for globally unique IDs.

Relationship types: MANAGES, WORKS_FOR, USES, HOSTED_ON, BELONGS_TO, MENTIONS, DERIVED_FROM, and PART_OF. Factual edges contain document/chunk IDs, an exact quote, extraction method, confidence, creation time, dataset scope, and fingerprint. Technology records represent project-specific instances, so PostgreSQL hosting facts cannot cross between Atlas and Atlas East.

Two schema migrations create **18 uniqueness constraints** including migration tracking, and **3 explicit range indexes**. Neo4j reports **23 indexes** including uniqueness backing indexes and its default lookup indexes. Applied migration versions are `001` and `002`; a rerun applied no files.

See [GRAPH_SCHEMA.md](GRAPH_SCHEMA.md) for directions, identity rules, constraints, indexes, and future entity resolution.

## 4. Fixture counts

| Nodes | Count |
| --- | ---: |
| Person | 8 |
| Organization | 3 |
| Project | 6 |
| Technology instance | 6 |
| Platform | 3 |
| Document | 12 |
| Chunk | 12 |
| **Fixture total** | **50** |

| Relationships | Count |
| --- | ---: |
| MANAGES | 6 |
| WORKS_FOR | 6 |
| USES | 6 |
| HOSTED_ON | 6 |
| BELONGS_TO | 6 |
| MENTIONS | 37 |
| DERIVED_FROM | 12 |
| PART_OF | 12 |
| **Total** | **91** |

There are **30 factual relationships**. The other 61 relationships describe mentions, membership, and excerpt derivation. Two migration records and one fixture lock bring this otherwise empty database to **53 physical nodes**. Repeated fixture loads preserved the same domain IDs, properties, and counts.

## 5. Exact tests passed and skipped

Final command: `uv run pytest --run-integration -q --junitxml=reports/all-tests.xml`.

**78 passed, 0 failed, 0 errors, 0 skipped**, in 61.19 seconds. This includes **60 unit tests and 18 real Neo4j integration tests**. No Docker-dependent check was skipped. [test-results.json](../reports/test-results.json) lists every test case and its status from the final JUnit report.

| Unit module | Passing cases |
| --- | ---: |
| API health/readiness, request IDs, safe errors, validation, redaction | 11 |
| Configuration, password/URI validation, bounds | 13 |
| Driver query parameters, pooling, error boundary, cleanup | 3 |
| Fixture import/reset safety guards | 5 |
| Deterministic fixtures, schema directions, evidence, distractors, evaluations | 24 |
| Migration ordering, failure reporting, checksums, duplicate versions | 4 |

All real integration checks passed:

1. Driver connectivity and successful query.
2. Connection outage against an unavailable local Bolt endpoint.
3. Migration records and constraints created.
4. Idempotent migration rerun.
5. Expected node and relationship counts after loading.
6. Repeated fixture loading without changes.
7. Full live-graph and provenance validation.
8. All 30 factual evidence references resolve.
9. Priya's two-hop path exists.
10. Priya's three-hop path reaches AWS.
11. Morgan's distractor path reaches Azure through its own instance.
12. Conflicting fixture data is rejected atomically.
13. Orphaned evidence is detected, with test changes rolled back.
14. Unsupported quote is detected, with test changes rolled back.
15. Missing edge is detected, with test changes rolled back.
16. Reversed edge is detected, with test changes rolled back.
17. Confirmed scoped reset preserves unrelated data and refuses external edges.
18. API health/readiness use the real database successfully.

Ruff lint and format checks passed. `uv lock --check` passed. The separate unit command passed all 60 cases in 1.77 seconds.

The real process exercise also passed ([runtime-verification.json](../reports/runtime-verification.json)):

| State | Health | Readiness |
| --- | ---: | ---: |
| Database connected | 200 | 200 |
| Compose Neo4j service stopped | 200 | 503 |
| Fresh API starts while database is stopped | 200 | 503 |
| Neo4j restarted and recovered | 200 | 200 |

Versioned readiness returned 200 and request-ID headers were present. The temporary verification API was stopped afterward; Neo4j was restored. A normal local API was then started on loopback port 8000 for inspection.

## 6. Sample evidence paths

Two hops:

```text
Priya --MANAGES [fact:001, doc:01]--> Atlas
Atlas --USES [fact:003, doc:02]--> PostgreSQL (Atlas instance)
```

Three hops:

```text
Priya --MANAGES [fact:001, doc:01]--> Atlas
Atlas --USES [fact:003, doc:02]--> PostgreSQL (Atlas instance)
PostgreSQL (Atlas instance) --HOSTED_ON [fact:005, doc:03]--> AWS
```

These are verified fixture paths. They are not generated answers from a finished retrieval system. The separate Atlas East chain reaches Azure. Six answerable evaluation paths were checked; the three unanswerable examples remain expected outcomes for a future QA evaluator.

## 7. Commands used

From `<research-workspace>`:

```powershell
uv sync
uv run python -m scripts.setup_env
uv run python -m scripts.build_fixtures
docker compose up -d --wait
uv run python -m scripts.graph migrate
uv run python -m scripts.graph load
uv run python -m scripts.graph validate
uv run ruff check . --fix
uv run ruff format .
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/unit -q --junitxml=reports/unit.xml
uv run pytest tests/integration --run-integration -q --junitxml=reports/integration.xml
uv run python -m scripts.verify_runtime
uv run pytest --run-integration -q --junitxml=reports/all-tests.xml
uv run python -m scripts.graph migrate
uv run python -m scripts.graph validate
uv lock --check
```

The runtime exercise launched a real `uvicorn app.main:create_app --factory` subprocess on a temporary loopback port. It ran `docker compose stop neo4j` and `docker compose up -d --wait neo4j`. A normal API process was subsequently launched with the virtual environment's Python and `-m scripts.serve`. Use `uv sync --locked` for future setup from this lockfile.

Verified environment: Python 3.12.13, Neo4j Community 5.26.32, Neo4j driver 6.4.1, FastAPI 0.162.0, Pydantic 2.14.1, pydantic-settings 2.16.1, Uvicorn 0.54.0, pytest 9.2.0, httpx 0.28.1, Ruff 0.17.3, uv 0.11.23, and Docker Engine 29.9.2. Exact Python transitive dependencies are in `uv.lock`.

## 8. Problems encountered and fixed

- Docker Desktop was stopped. It was started, and the pinned Community image was pulled and health-checked.
- The initial import exceeded the five-second query timeout on this machine. The transaction rolled back. Imports now use their own configurable timeout, default 60 seconds, while readiness keeps a short query timeout. The load then passed.
- The newest Starlette TestClient path warned about its httpx transition. API tests now use direct httpx ASGI transport with explicit application lifespan, removing that warning without extra dependencies.
- Initial lint and formatting findings were corrected.
- A full test run overlapped the deliberate database outage. Its database checks failed, as expected. The final suite was rerun after confirmed recovery and passed all 78 cases. Outage verification and database tests must run sequentially.
- Reset protection was made atomic and tested against an external edge. The refused reset preserved data; the subsequent permitted reset removed only its uniquely scoped test fixture.

## 9. Remaining risks and limits

This is a local foundation with a small manually curated corpus. Integrity checks prove agreement with the fictional sources, not general natural-language truth. There is one chunk per document and one cited assertion per fact edge. Future ingestion needs source versioning, reviewed entity resolution, conflict handling, and richer evidence aggregation.

Schema migrations are single-writer maintenance operations and commit DDL statements separately. Partial failure is recoverable through idempotent statements; there is no automatic rollback framework. Direct database writes can bypass application-level provenance requirements, so run validation after manual Browser changes.

The loopback API and Community database are for local development. Production authentication, authorization, TLS, backups, deployment, and operational hardening are future decisions. No vector baseline, retrieval benchmark, or LLM answer quality has been measured. No benchmark improvement is claimed.

## 10. Stage 1 verdict

**PASS.** The foundation works against real Neo4j. Facts retain their sources. The required two-hop and three-hop paths are present. Health and readiness behave correctly through a real outage and recovery. All final checks passed, with no skipped integration tests.

In simple English: the project can now store a small set of fictional documents, connect the facts they support, and prove where each fact came from. It is ready for a separately requested next stage. It does not answer new user questions yet.
