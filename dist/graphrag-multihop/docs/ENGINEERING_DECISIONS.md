# Engineering decisions

| Decision | Reason | Cost and limit |
|---|---|---|
| Finite extraction and question grammars | Auditable, repeatable source proof without paid APIs | Low recall on legitimate new phrasing |
| Scoped, typed identities and abstention on ambiguity | Avoid silent merges of homonyms or project-specific databases | Requires source-supported context; not general entity linking |
| Preserve actual multi-hop paths | Expose why an answer follows from source facts | More database work than an unchecked direct shortcut |
| Source/run hashes and final revalidation | Reject stale, forged or incomplete publications | Repeated reads and a large fixed seal cost |
| Maximum three hops, 128 candidates, ten answers | Bound traversal and reject incomplete answer sets | Some valid larger answers deliberately abstain |
| Local pinned MiniLM in a supervised CPU process | Free deterministic embeddings; offline inference and bounded worker failure | Single-worker contention and cold model cost |
| Preserve the frozen vector answerer | Keep the historical baseline reproducible | Stage 6 new plural forms fail even when retrieval finds evidence |
| Hybrid answers require graph proof | Additional text must not create an unsupported conclusion | More text coverage does not expand the answer grammar |
| Separate publication package | Protect research data and remove credentials/caches | Documentation and packaging differences need an explicit audit trail |

The Stage 7A connection pool experiment changed only the configured maximum from ten to 50. It kept acquisition at three seconds, graph/hybrid request budgets at 20/60 seconds and read managed retries at zero. On the same 50-user two-wave workload, graph errors fell from 56/100 to 0/100 and hybrid from 17/100 to 0/100. The publication environment template uses 50; the research default and original results remain unchanged. Graph p95 increased from 4.18 seconds to 17.27 seconds because more requests completed expensive graph work instead of failing early. Hybrid p95 was 17.66 versus 17.91 seconds. This is a measured configuration improvement, not a throughput or production-readiness claim.

All measured runs saturated the one-CPU host. At pool 50 the hybrid embedding-lock wait p95 was 15.02 seconds and lock hold p95 0.73 seconds. Historical path validation incurred 16/18/20 database round trips for one/two/three hops. A higher pool does not remove CPU limits, the serialized model or repeated seals. Further changes should compare proof-equivalent batching, admission limits and model scheduling on repeated sustained HTTP workloads before changing architecture.

The historical 49 graph and 14 hybrid errors per 100 requests remain part of the record. They cannot be retrospectively given exception traces that were never captured. A supplemental historical diagnostic and the new controlled repeat both identify ConnectionAcquisitionTimeoutError. The new repeat logged 56 graph and 17 hybrid causes of that exact type, with no measured driver transport or request-deadline exceptions. An earlier Stage 7A warm-up did fail with a Bolt handshake timeout before measurement; it was preserved, and bounded readiness polling preceded the recorded trials. No measured retries were added.

Driver-internal active/idle connection occupancy was not sampled. The acquisition exceptions, ten configured connections versus 50 service threads, and the paired pool-size change support a pool-acquisition bottleneck; the reports do not invent a measured occupancy percentage. The one sequential before/after pair also has cache, scheduling and order effects, so its zero-error result needs broader repetition before a capacity claim.

This workload calls services through ThreadPoolExecutor and is not an HTTP server capacity test. Synchronous API handlers use a worker pool, including health/readiness; saturation could delay them, but event-loop or HTTP admission measurements were not performed. The application keeps fixed safe API errors, while offline diagnostic reports record only exception type/code flags, not passwords or source payloads.

Production work remains separate: authentication and authorization, resource admission, repeated HTTP load tests, more representative externally held-out questions, richer extraction and grammar, a tested publication licensing choice, model/dependency lifecycle review and hosted CI verification. None is implied by passing functional tests. See [STAGE7A_RELEASE_REPORT.md](STAGE7A_RELEASE_REPORT.md).
