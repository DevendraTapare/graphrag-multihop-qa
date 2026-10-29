# Graph security and adversarial verification

The graph endpoint accepts a question and a strict integer hop cap of one to three. It exposes no query language. Question fragments never become Cypher identifiers or clauses. Closed enum templates restrict labels, stored relationship direction, and exact path lengths. The starting canonical ID is parameterized; structural links cannot become reasoning steps.

`tests/unit/test_graph_rag.py` verifies typed plans, aliases, Unicode normalization, duplicate identities, explicit context, unsupported grammar, oversized/invalid inputs, injection strings, safe templates, deadlines, baseline hashes, and runtime independence from vector/evaluation imports. `test_graph_api.py` checks safe 422/503/504 responses and request IDs. `test_graph_evaluation.py` checks source-copy normalization and distinguishes text coverage from actual graph chains.

`tests/integration/test_graph_rag.py` runs against a fresh uniquely named Neo4j Community 5.26.32 container on an ephemeral loopback port. Mutations never use the development graph or its volume. Cleanup refuses the development URI. The fixture uses the normal three-second connection bound for sustained graph tests; production request/query bounds remain unchanged.

| Database-sensitive scenario | Required result |
| --- | --- |
| Similar projects and deployment instances | Correct distinct canonical endpoints |
| Duplicate people / ambiguous project alias | Explicit ambiguity; no first match |
| Reversed relationship or wrong deployment endpoint | Rejected proof or no approved path |
| Unrelated nearby node, cycle, direct shortcut | Cannot supply the requested chain |
| Several paths with one answer | All validated supports retained |
| Conflicting answers | Singular abstention, plural complete bounded set |
| Missing intermediate or incomplete branch | Abstention, even if another branch completes |
| Missing/orphaned chunk or deleted document | Invalid source cannot support an answer |
| Corrupted text/hash/quote, stale processing, failed run | Invalid source cannot support an answer |
| Corrected hosting source | Old assertion hidden; current assertion used |
| One failed source and another valid source | Valid independent support survives |
| Forged curated ID / modified curated assertion | Rejected; valid automatic support may survive |
| High-confidence unapproved inference | Ineligible |
| Structural links replacing facts | Abstention |
| Candidate/answer overflow | Abstention; no arbitrary truncation |
| Vector index removed | Graph retrieval still works |
| Actual query capture | Bounded exact templates, parameters, timeouts; no vector call |
| Source changes during validation | Safe graph_snapshot_changed error |
| Actual Bolt outage and recovery | Safe failure then working query |
| Concurrent graph and API queries | Deterministic proof and separate request IDs |

The full test run includes all Stage 1–3 regressions and the real local MiniLM integration tests. See `reports/stage4-tests.xml` and `reports/stage4/test_results.json` for final counts and zero-skip evidence. `scripts.verify_graph` independently checks every current eligible factual assertion in the development graph. `scripts.verify_graph_runtime` exercises a real Uvicorn process and HTTP requests, stops Compose Neo4j, restarts the API during the outage, restores Neo4j in a finally block, and verifies recovery. It preserves the volume. Run outage verification sequentially after database tests.

```powershell
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run pytest --run-integration -q --tb=short --junitxml=reports/stage4-tests.xml
uv run python -m scripts.verify_graph
uv run python -m scripts.verify_graph_runtime
```

Limits: this is a local unauthenticated development API, not a public production service. It has bounded per-request work but no global rate limiter or admission controller. Revalidation detects changes across reads but cannot prevent a source changing after the last check. A deadline is checked between bounded operations; it is not hard process cancellation. The reviewed registry and grammar restrict recall. A fixed approved source set requires explicit publication review for new inputs. Large or adversarial source collections would need stronger indexing, publication isolation, quotas, and load testing. These limits do not authorize unsupported answers.
