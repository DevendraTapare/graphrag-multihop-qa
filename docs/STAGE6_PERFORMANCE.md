# Stage 6 performance

This measures the unchanged frozen runtime. It does not establish production scalability.

## Sequential evaluation

| Mode | Document-held-out p50/p95 ms | Template-held-out p50/p95 ms | All final questions p50/p95 ms |
| --- | ---: | ---: | ---: |
| Vector | 110.41 / 242.73 | 103.39 / 196.55 | 105.66 / 225.07 |
| Graph | 279.60 / 615.64 | 0.06 / 0.18 | 0.12 / 475.62 |
| Hybrid | 381.87 / 1102.76 | 105.87 / 195.57 | 131.36 / 691.43 |

The all-final graph median mostly measures unsupported-template rejection without a database read. Compare the document-held-out distribution and actual supported PROFILE probes for traversal costs. Model startup is excluded from warm quantiles. Inputs and configuration hashes, Python/Neo4j/model versions, hardware and both full scored runs are retained. The machine reports one physical/logical CPU and approximately 14.9 GB RAM. Three persistent local Neo4j instances were running; historical instances received no benchmark traffic. No load, outage or regression tests overlapped scoring. No OS cache flush was performed.

## Bounded load

Two closed-loop waves per user count, one request per thread per wave; separately per mode. Calibration probes span one-/two-/three-hop chains and one absent-entity query. The smallest levels do not have identical probe proportions to the larger levels. Primary total: 546 requests across all fifteen mode/level combinations. Full raw outcomes, database call wall times, embedding lock-inclusive times and resource samples are in load_results.json.

| Mode | Users | Requests | Answers | Correct abstentions | False abstentions | Errors | Explicit request-budget timeouts | p50/p95 ms | Completed requests/s | Correct results/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Graph | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 458.73 / 479.04 | 2.15 | 2.15 |
| Graph | 5 | 10 | 8 | 2 | 0 | 0 | 0 | 1704.84 / 2753.13 | 2.22 | 2.22 |
| Graph | 10 | 20 | 16 | 4 | 0 | 0 | 0 | 2119.27 / 2472.44 | 4.21 | 4.21 |
| Graph | 25 | 50 | 29 | 12 | 0 | 9 | 0 | 2997.96 / 4593.66 | 5.44 | 4.46 |
| Graph | 50 | 100 | 27 | 24 | 0 | 49 | 0 | 2996.37 / 3927.97 | 11.11 | 5.67 |
| Vector | 1 | 2 | 1 | 0 | 1 | 0 | 0 | 134.85 / 142.80 | 7.33 | 3.66 |
| Vector | 5 | 10 | 3 | 2 | 5 | 0 | 0 | 460.37 / 2156.17 | 3.69 | 1.84 |
| Vector | 10 | 20 | 5 | 4 | 11 | 0 | 0 | 857.64 / 1629.71 | 6.43 | 2.89 |
| Vector | 25 | 50 | 13 | 12 | 25 | 0 | 0 | 2410.58 / 3791.10 | 6.78 | 3.39 |
| Vector | 50 | 100 | 25 | 24 | 51 | 0 | 0 | 3358.75 / 6545.64 | 7.40 | 3.63 |
| Hybrid | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 1191.60 / 1783.80 | 0.84 | 0.84 |
| Hybrid | 5 | 10 | 8 | 2 | 0 | 0 | 0 | 1791.50 / 3572.10 | 1.52 | 1.52 |
| Hybrid | 10 | 20 | 16 | 4 | 0 | 0 | 0 | 3523.08 / 7198.08 | 1.77 | 1.77 |
| Hybrid | 25 | 50 | 38 | 12 | 0 | 0 | 0 | 5674.99 / 8965.93 | 2.76 | 2.76 |
| Hybrid | 50 | 100 | 66 | 20 | 0 | 14 | 0 | 10759.61 / 18997.96 | 2.76 | 2.37 |

Completed throughput counts failures as completed requests. Correct-results throughput includes correct answers and correct abstentions, not false abstentions or errors. No result should be called a capacity guarantee. Explicit request-budget timeout categories were zero; database errors include acquisition/read timeouts. One driver socket read timeout is retained in the primary log; supplementary cause instrumentation found 28 pool-acquisition timeouts in 50 graph requests, with limits and queries unchanged. The supplementary numbers are not substituted for the primary failures.

At 50 users, database call wall p50/p95 and embedding contention were:

| Mode | Database call wall p50/p95 ms | Embedding lock-inclusive p50/p95 ms |
| --- | ---: | ---: |
| Graph | 127.92 / 2998.97 | 0.00 / 0.00 |
| Vector | 35.81 / 274.36 | 2853.77 / 6168.87 |
| Hybrid | 140.75 / 737.55 | 6774.80 / 12998.67 |

Database wall time includes pool acquisition, network and server work. It is not server CPU time. In the supplementary diagnostic, Neo4j summary available-after p50/p95 was 2.00 / 173.65 ms and consumed-after was 9.50 / 189.90 ms. Those driver summary fields exclude connection-pool wait and are not pure execution CPU. Internal pool occupancy is unavailable through the supported public API; configured size is ten. The single local embedding worker serializes inference. Lock-inclusive timings include both waiting and inference, not a separately measured wait counter.

Host CPU reached 100%. JSON samples record host used memory and runner RSS; they do not isolate model-worker or database-container RSS. Short bursts, OS scheduling and the shared Docker/Windows host limit comparisons.

## Actual query plans

PROFILE was executed on actual calibration paths and source/provenance reads with trusted parameters. One-/two-/three-hop graph requests made 16/18/20 round trips. Unique PROFILE query sets contain NodeUniqueIndexSeek for entity/source/run/document lookups and DirectedRelationshipUniqueIndexSeek for sealed assertion IDs. Path expansion is typed, explicitly one to three hops, and capped. There is no unbounded relationship expression or user-authored Cypher.

Capture and final revalidation repeat source-publication checks, path prefixes and batched metadata reads intentionally. Metadata is batched, rather than one query per individual fact, but repeated full-publication validation adds fixed work. The whole:Chunk ingestion lookup uses NodeByLabelScan: on the three-hop probe it produced 633 scan rows and 636 DB hits for 211 physical chunks. The source proof reconstructs approved source facts with a request-local cache. Exact profiles, parameters, DB hits and driver server summary timings remain in query_plans.json.

Measured bottlenecks are many round trips, the metadata scan, full-publication checks, pool acquisition and serialized embeddings. No safety/provenance check was removed, no pool/retry limit was silently widened and no index/runtime optimization was made after freezing. A future calibration-only experiment could measure a chunk ingestion index or fewer round trips while preserving snapshot/provenance semantics; that work is not started here.
