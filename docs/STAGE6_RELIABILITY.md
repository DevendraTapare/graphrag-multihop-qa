# Stage 6 reliability and recovery

The real exercise used only compose.stage6.yml, project graphrag-stage6, ports 27476/27689 and its own persistent volume. The historical containers and volumes stayed running. All captured request/result phases are in recovery_results.json; recovery_attempt.json preserves partial/final state as well.

## Measured sequence

API startup to liveness: 2.71s. Initial fresh API/model hybrid query: 22.82s. A separate in-process model was then loaded before the outage. The database was stopped after the first actual path read of an in-flight request, before remaining source proof/revalidation. This tests interruption between real read phases, not interruption in the middle of a single server operator. That request failed safely after 8.01s; the time includes the coordinated stop. It returned no partial answer.

During outage, all three HTTP modes returned safe 503 bodies with request IDs and no answer/path. Liveness remained 200; aligned readiness was 503. The API was restarted while Neo4j was down and remained live/unready. No fallback answer was generated.

| Measurement | Time |
| --- | ---: |
| Start command through Bolt readiness | 53.78s |
| Vector-index readiness check after Bolt | 1.85s |
| First graph query after readiness, model already loaded | 19.24s |
| Next vector query, same loaded model | 5.40s |
| Next hybrid query, same loaded model | 2.06s |
| Fresh driver connection/readiness after warming | 67.54ms |
| Fresh API/model hybrid query after recovery | 18.23s |

Order matters: graph, then vector, then hybrid share database warm-up. The fresh connection probe is measured after database warm-up and cannot be used to subtract a first cold handshake. Bolt readiness does not guarantee warm query plans or caches. The first graph request spent 17.02s in capture/traversal including the global publication seal, 1.48s in provenance and 0.74s in revalidation. Pure path CPU, disk I/O, plan compilation and JVM/OS warm-up were not separately measured within that capture phase. Actual PROFILE plans provide a separate warm-query view.

The fresh API/model recovered request spent 15.77s in model startup/embedding, 0.82s in vector search, 0.84s in graph capture, 0.05s in provenance and 0.54s in revalidation. Its HTTP wall total was 18.23s. Subsequent hybrid HTTP wall times were 13.83s, 3.33s, 1.63s, 1.02s, 1.39s. These remain variable and are not all subsecond.

## Why Stage 5's 20.02 seconds needs caution

Both cold model startup and cold database query work can be substantial. The Stage 5 timing was one first recovered request without this full decomposition. Stage 6 does not prove its exact cause retrospectively. The new measurements show a loaded-model graph request near twenty seconds and a fresh-model hybrid request near eighteen seconds. Database process startup is another 53.78-second interval before either query measurement.

## Bounds and safety

Read driver managed retry time remains zero. Application reads use auto-commit session.run, not a hidden managed retry loop. Ingestion alone uses managed writes with a three-second retry maximum. Connection/acquisition timeout remains three seconds, pool maximum ten, graph query maximum ten seconds bounded by remaining budget, graph request target twenty seconds and hybrid target sixty seconds. Neo4j Query transaction timeouts and remaining-budget checks remain intact. [Official query manual](https://neo4j.com/docs/python-manual/current/query-simple/) and [driver configuration/API](https://neo4j.com/docs/api/python-driver/current/api.html) describe these distinct controls.

Budgets are checked between bounded operations; this is not a hard OS cancellation deadline. Load errors show that deadlines do not guarantee successful recovery/capacity. Index readiness is checked separately from database connectivity. The readiness endpoint checks connectivity only, not model warmth, full source publication or answerability. Final provenance revalidation is not atomic through HTTP delivery. No safety check was disabled to improve latency.
