# Stage 2 report: automatic knowledge graph construction

Verified on **28 October 2026**, Asia/Calcutta. **Verdict: PASS.** Stage 2 is complete. Stage 3 has not started.

The project now reads controlled fictional documents, finds supported entities and relationships, checks their exact source evidence, and writes them safely to real Neo4j. Old, failed, and unfinished ingestions are excluded from eligible evidence. Existing curated facts remain intact.

## Files created or changed

The complete inventory and the list of changed Stage 1 files are in [STAGE2_FILE_MANIFEST.md](../reports/STAGE2_FILE_MANIFEST.md).

There are **40 new shareable files** and **16 changed Stage 1 files**, for **103 shareable files** in the current project.

Main additions:

- `app/extraction/`: strict candidate models, local document loading, exact-offset chunking, a controlled registry, the extractor interface/rules, independent provenance validation, and the pipeline.
- `app/repositories/ingestion.py`, `app/services/ingestion.py`, and `app/services/ingestion_validation.py`: managed write transactions, source claims, lifecycle records, publication, source failure handling, audits, rejected candidates, and conflict inspection.
- `app/evaluation/extraction.py` and reproducible authoring/evaluation scripts.
- `migrations/003_ingestion_lifecycle.cypher`: two operational uniqueness constraints and three range indexes.
- Four local TXT/Markdown documents, a reviewed alias registry, and a labeled extraction dataset.
- Three unit-test modules, one real integration-test module, documentation, and machine-readable verification artifacts.

Existing files were updated for configuration, the ingestion CLI/runtime workflow, schema documentation, and Stage 1 compatibility. The Stage 1 fixture validator now distinguishes ingestion-owned assertions from unexpected unowned edges. The fixture loader batches trusted queries while retaining its complete collision checks and atomic transaction. The legacy migration regression explicitly expects versions 001, 002, and 003. Original migration files and curated fixture identifiers/properties were preserved.

No runtime dependency was added. `uv.lock` remains valid. No paid model calls, GitHub repository, Git commit/push, deployment, or HTTP mutation endpoint was introduced.

## Documents processed and extraction counts

[stage2-corpus-verification.json](../reports/stage2-corpus-verification.json) records the complete two-pass corpus exercise under the final processing version.

| Corpus result | Measured count |
| --- | ---: |
| Documents processed | **16** |
| Existing Stage 1 fixture documents | 12 |
| New local TXT/Markdown documents | 4 |
| Raw entity mention candidates | 99 |
| Resolved entity mentions | 97 |
| Unique canonical entities referenced | **27** |
| Relationship candidates | 40 |
| Accepted automatic factual relationships | **38** |
| Rejected candidates across all candidate kinds | **8** |
| Successful source provenance audits | 16 |

The 27 canonical entities comprise the 26 existing fixture entities plus one distinct Cedar employee named Priya. They are not 27 duplicate new entity nodes. The 38 automatic assertions have their own source/span/version IDs and remain distinguishable from the 30 curated assertions. Equal triples from different sources retain independent support.

All 16 documents were ingested twice. Summaries, eligible assertion IDs, and complete assertion properties were identical after the repeat. The review document completed with zero accepted facts and explicit rejection reasons. Rejected-candidate count includes entity, relationship, and sentence decisions; it is not the subtraction of relationship totals alone.

Corpus counts exclude temporary integration-test sources and the separate extraction evaluation. Historical diagnostic/earlier processing records may remain physically stored; only the current version's ready source/run assertions are eligible.

## Measured extraction quality

The separate labeled evaluation contains **53 documents**, **110 entity examples**, **32 positive relationship examples**, **10 ambiguous identity cases**, and **12 unsupported/misleading cases**. Gold labels are explicitly authored without calling the extractor. Calibration and held-out cases have different texts and IDs.

| Metric | Combined | Held-out split |
| --- | ---: | ---: |
| Entity precision | **100%** (110/110) | **100%** (58/58) |
| Entity recall | **100%** (110/110) | **100%** (58/58) |
| Relationship precision | **100%** (30/30) | **100%** (15/15) |
| Relationship recall | **93.75%** (30/32) | **88.24%** (15/17) |
| Canonical ID resolution accuracy | **100%** | **100%** |
| Incorrect canonical assignments / measured merges | **0** | **0** |
| Unsupported accepted facts | **0** | **0** |
| Provenance accuracy | **100%** | **100%** |
| Rejected candidates | 34 | 20 |

The two false negatives use “oversees” and “depends on,” which are outside the approved relation grammar. They were not removed from the score. These measurements describe the synthetic fictional domain, not general-purpose extraction. The held-out split was inspected while fixing a prefix bug, so it is not a blind independent generalization estimate. Definitions and limitations are in [EXTRACTION_EVALUATION.md](EXTRACTION_EVALUATION.md); raw per-case measurements are in [extraction-evaluation.json](../reports/extraction-evaluation.json).

## Provenance, identity, and lifecycle

Automatic documents are immutable content-hash snapshots. Their IDs are separate from the original curated document IDs. Chunks preserve exact original text, Unicode character offsets, document hash, and processing version. Entities use a reviewed alias registry; ambiguous names require explicit valid context or rejection. Atlas/Atlas East and their PostgreSQL deployments remain separate.

Before writing a fact, the validator checks source/hash/version, complete original evidence span, grounded endpoint mentions, approved positive grammar, relationship direction/types, canonical identities, and deterministic IDs. Context used to disambiguate a fact is rebuilt from approved source statements, not trusted from candidate output. Fake extractor context and fenced code cannot make an ambiguous relationship accepted.

The writer checks persisted document/chunk evidence and endpoint labels within managed transactions. All data values are parameterized; labels and relationship types use closed allowlists. Small batches stage data, then an atomic publication step verifies completeness and sets the source's current ready run. Current-version readers exclude stale, processing, failed, or unverified assertions.

The source claim uses a token, write lock, and renewable lease. Tests prove a second active writer is refused, expired interruptions can be recovered, stale tokens cannot publish, actual managed retries do not duplicate facts, and repeated publication is idempotent.

Changed content clears the old current pointer before processing. A local source that becomes missing, deleted, or corrupt is marked failed when refreshed, hiding only its own support. Restoring and reprocessing can reuse valid IDs. Independent source evidence and curated data are retained. No incomplete ingestion is marked ready.

`verified_rule` describes source/pattern validation, not objective real-world truth. Rule score 1.0 is not a calibrated truth probability. Conflicting hosting claims remain separately sourced and are flagged as potential conflicts for review rather than overwritten.

## Unit, integration, and regression results

Final full command:

```powershell
uv run pytest --run-integration -q -x --tb=short --junitxml=reports/stage2-all-tests.xml
```

**180 passed, 0 failed, 0 errors, 0 skipped**, in 76.76 seconds. This is **141 unit tests and 39 real Neo4j integration tests**, including all **78 Stage 1 regression cases**. Every case and status appears in [stage2-test-results.json](../reports/stage2-test-results.json).

| Test group | Passed |
| --- | ---: |
| Existing Stage 1 unit cases | 60 |
| New loading/chunking unit cases | 27 |
| New provenance/adversarial unit cases | 17 |
| New extraction/resolution/evaluation unit cases | 37 |
| Existing Stage 1 real Neo4j cases | 18 |
| New real ingestion cases | 21 |

The new real tests cover correct persistence/provenance, repeated ingestion, independent sources, similar identities, reviewed rejections, incomplete publication, missing persisted chunks, failed staged data and reprocessing, changed sources, mid-processing source changes, stale extraction/configuration, lease recovery, concurrent writers, actual retry/replay, conflicts, tampered provenance, connection outage/recovery, empty input, deleted source files, and corrupt UTF-8 refreshes. Test-created sources are cleaned up by their exact unique IDs; canonical/curated records are retained.

Ruff lint, Ruff format checks, and `uv lock --check` passed. A CLI smoke check confirmed `--chunk-size 0` exits with a validation error before database initialization. Normal CLI inspection also passed: ready summary, valid provenance, seven review-document rejections, two independently supported potential conflicts, and ingestion-history listing ([CLI evidence](../reports/stage2-cli-verification.json)). Invalid paths, encoding, labels, offsets, directions, aliases, negations, prompt-like instructions, fabricated context, and code-example context are tested.

The unchanged Stage 1 namespace still validates to **50 nodes, 91 relationships, and 30 factual relationships**. Its two-hop and three-hop Priya paths still lead through Atlas/PostgreSQL to AWS. Schema versions 001–003 verify successfully; rerunning migrations applies no files. The schema now has 20 project uniqueness constraints and 6 explicit range indexes.

## Actual outage and recovery

[stage2-runtime-verification.json](../reports/stage2-runtime-verification.json) records a real API process and actual Compose service stop/start after the final provenance change.

| State | Health | Readiness | Ingestion |
| --- | ---: | ---: | --- |
| Connected | 200 | 200 | Ready sources available |
| Neo4j stopped | 200 | 503 | Safe `database_unavailable` failure |
| Fresh API starts during outage | 200 | 503 | No ready facts created by failed attempt |
| Neo4j recovered | 200 | 200 | Atlas ready again with 3 audited facts |

Request IDs and versioned readiness also passed. The script restored Neo4j and stopped its temporary API. The existing review API uses loopback port 8000; Neo4j Browser uses loopback port 7474.

The old Java-based container health probe accumulated orphan `cypher-shell` JVMs when it timed out. It was replaced with an HTTP probe using Bash builtins, and only this Compose container was recreated, preserving its data volume. Application readiness still verifies an authenticated database query. A 60-second shutdown grace period was added.

## Commands used

```powershell
Set-Location <research-workspace>
uv run python -m scripts.build_registry
uv run python -m scripts.build_extraction_evaluation
docker compose --progress plain up -d --wait
uv run python -m scripts.graph migrate
uv run python -m scripts.ingest ingest atlas.txt
uv run python -m scripts.verify_ingestion
uv run python -m scripts.evaluate_extraction
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run pytest tests/unit -q
uv run pytest tests/integration/test_ingestion.py --run-integration -q -x --tb=short
uv run pytest --run-integration -q -x --tb=short --junitxml=reports/stage2-all-tests.xml
uv run python -m scripts.verify_runtime
uv run python -m scripts.ingest validate source:b957fc6f9a3c7019b71c79196908b4beb597c79a
```

Run outage verification sequentially after database tests. Two CLI inspection calls that overlapped a planned outage returned the expected safe unavailable error; normal inspection was repeated after recovery. Use `uv sync --locked` for setup on another machine and follow README prerequisites.

## Problems found and fixed

- Unknown longer names could be shortened to a registered prefix. Unknown longer identities now outrank prefixes and require review.
- A rooted Windows filename could escape the intended path-validation loop. Rooted, absolute, drive, UNC, and traversal paths are rejected before traversal or database work.
- High configured overlap could prevent an otherwise short sentence from fitting any chunk. Overlap is reduced when necessary while preserving source coverage and offsets.
- Slow Java health probes accumulated orphan processes and caused database timeouts. The new built-in HTTP probe avoids those processes.
- The Stage 1 loader's many individual queries hit a cold-start transaction timeout. It now batches equivalent trusted MERGE operations and collision checks within the same atomic transaction.
- Candidate-supplied context could make an ambiguous identity look resolved. Context and mention spans are now independently reconstructed and checked against the source; a new processing version invalidates older output for current readers.
- Missing/corrupt refreshed sources now create failed lifecycle records and hide their old eligible assertions without removing independent support.

All failing development checks were corrected and rerun. Required integration checks were not skipped.

## Remaining limitations and verdict

The grammar and identity registry cover a small fictional domain. Unsupported paraphrases, unknown people/organizations, complex coordination, and ambiguous deployment references need review. There is no automatic general-purpose entity discovery or semantic entailment model.

Source history and incomplete physical batches remain stored; no garbage collection is implemented. Reader eligibility gates are mandatory. The system has no filesystem watcher or atomic transaction spanning local file changes and Neo4j; refresh modified/removed sources through the CLI. Direct database administrators can bypass application rules and should audit after manual changes. Schema migrations remain single-writer maintenance operations.

**PASS:** documents load automatically, offsets and evidence are preserved, unsafe merges are rejected, graph writes and retries are idempotent, source updates/failures remain safe, measured extraction quality is reported, and all previous and new real-database tests pass. No retrieval benchmark improvement is claimed. Stage 3 has not started.
