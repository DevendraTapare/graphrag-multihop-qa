# Stage 5 security and regression verification

Stage 5 keeps source-only construction separate from offline labels. The builder and runtime cannot import evaluation code or read evaluation JSON. A unit check inspects those imports/file references. Source-derived assertion manifests are integrity checks only; the answerer must still retrieve actual Neo4j paths and independently verify each supporting source.

The original Stage 1–4 files and graph were archived before changes. Historical metrics, registry, extraction, vector runtime, graph runtime and source fixtures remain byte-identical. Only the seven shared integration/documentation files listed in the Stage 5 inventory may change. The original graph snapshot must retain SHA-256 `449ea1c1703fcecf7a75f2445102d9de19a5b7c8624fd41985675ce154a57a63`. All Stage 5 source backfill/index writes use `compose.stage5.yml` and its own persistent volume. Database-sensitive adversarial mutations use another disposable container, with guards refusing both persistent database URIs.

## Tested controls

| Scenario | Required behavior |
| --- | --- |
| Source-driven employee homonyms | Separate canonical IDs; bare name ambiguous |
| Similar organizations and projects | Exact full identity; no prefix merge |
| Same project name with different owners | Distinct scopes; unqualified usage rejected |
| Reviewed product aliases | One product within one deployment; separate project instances |
| Unknown longer vector mention | Do not shorten into a known entity candidate |
| Wrong direction or deployment endpoint | No approved complete proof |
| Independent complete branches | Return all supported answers |
| Missing known intermediate branch | Abstain even when another path completes |
| Deleted first-hop branch after publication | Sealed build error; no partial-set answer |
| Invalid distinct first-hop evidence | Abstain; do not hide the branch |
| Orphaned chunk / stale source / failed run | Invalid support cannot authorize an answer |
| Corrected source version | Old assertion hidden; fixed evaluation build requires republishing |
| One failed source with another valid support | Underlying proof service retains independently valid assertion |
| Contradictory hosting for one deployment | Preserve alternatives and abstain |
| Cycles or unsupported shortcut | Cannot replace required directed hops |
| Candidate/answer cap | Conservative abstention; no truncated answer set |
| Corrupt vector metadata | Explicit dependency error; no silent graph fallback |
| Prompt-like, quoted, fenced, negated, or speculative source text | No unsupported accepted fact |
| Cypher-like query text | No query interpolation, mutation or fabricated path |
| Oversized question, bad top_k/max_hops, extra fields | Safe 422 before service execution |
| Driver, timeout or internal failure | Safe 503/504/500; no internal detail or answer |
| Concurrent queries | Stable proof, separate request IDs |
| Actual database stop and recovery | Health remains live, isolated readiness fails, query safely fails then recovers |

The new unit tests are `tests/unit/test_aligned.py` and `test_hybrid_api.py`. Real Stage 5 cases are in `tests/integration/test_aligned.py`. All existing Stage 1–4 tests run unchanged except the expected route inventory. Earlier database-sensitive coverage also exercises deleted documents, forged assertions, source-change races, indexing publication races and independent curated/automatic support. Final counts and zero-skip results are recorded in `reports/stage5/test_results.json` and local `reports/stage5-tests.xml`.

The independent full-source audit checks all 150 current automatic assertions: canonical endpoints, exact original quotes and offsets, current source/run versions, deterministic rule proof, complete chunks and structural provenance. It writes `provenance_audit.json` and the aligned snapshot. Identity checks write `identity_audit.json`. Backfill and vector indexing are each repeated without accumulating duplicates. Evaluations are repeated under the final runtime freeze; timing/request-ID fields are excluded from equality checks, not quality, source, score or path fields.

The first development evaluation was superseded after a completeness review found that path enumeration alone cannot detect a deleted entire first-hop branch. The source-only publication seal and invalid-distinct-branch checks were added before the final repeated runs. Conservative longest-mention candidate matching was also added to prevent known project prefixes from appearing as identities of longer names. These changes were tested on independent source examples; no individual question's gold answer or path was imported or repaired. `runtime_freeze_initial.json` and `development_evaluation_summary.json` preserve the development record; `runtime_freeze.json` identifies the final runtime.

`scripts.verify_stage5_runtime` starts a real temporary Uvicorn process, queries all three aligned modes, verifies a three-hop response, sends concurrent requests, stops only the Stage 5 Compose database, restarts the API during the outage, restores Stage 5, and verifies recovery. Historical database readiness stays available throughout. Its finally block restores the service and stops the owned API/model process tree. Run this check sequentially after measurements and before/after tests, never during shared performance work.

```powershell
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run pytest --run-integration -q -x --tb=short --junitxml=reports/stage5-tests.xml
uv run python -m scripts.verify_aligned
uv run python -m scripts.verify_stage5_runtime
```

## Remaining limits

This is an unauthenticated loopback development service, not a public production API. There is no global admission control or rate limiter. Explicit query/request/source/path limits bound current work, but the model/driver's own call deadlines and application checks do not provide hard process cancellation. Revalidation detects changes across reads and cannot stop a source changing after the final read. The fixed publication seal deliberately trades availability for complete shared-corpus consistency; a failed approved source can make the sealed build unavailable until rebuilt. Proof verifies support in controlled fictional sources, not external truth. Tests cover specified scenarios, not all possible adversarial natural language or indistinguishable real-world identities. Small local concurrency checks do not establish production capacity.

The unchanged vector baseline retains the documented Stage 3 top_k=1 incomplete-set failure. The Stage 5 comparison uses top_k=5 and observes no unsupported final answers. This is not a new guarantee that the frozen vector answerer is safe for every k, corpus or question. Hybrid's final answer policy requires complete graph proof regardless of the vector answer candidate.
