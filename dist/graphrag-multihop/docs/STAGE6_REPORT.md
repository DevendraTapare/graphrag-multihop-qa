# Stage 6 report

Verdict: **CONDITIONAL**. The evaluation and reliability work is complete, but language generalization and high-concurrency reliability remain weak. This is a NEW CONTROLLED CHALLENGE SET, not an independent external benchmark.

## What changed

Only README.md and docs/PROJECT_ROADMAP.md changed among the 241 existing files. New files provide the isolated challenge, source-only builder/runtime adapter, frozen evaluator, load/PROFILE/recovery tools, CI workflow, tests, six Stage 6 documents and retained reports. The complete hashed list is in reports/stage6/FILE_MANIFEST.md. No app implementation, historical fixture, migration, dependency lock or Stage 1–5 metric file changed. Both historical databases remain unchanged.

## Verification

**423 tests passed: 294 unit and 129 real Neo4j integration. Zero failures, errors or skips. All 412 previous tests remain present and pass.** This includes migration, extraction, provenance, filesystem, vector, graph, hybrid and adversarial checks. Ruff lint/format and the locked dependency check pass. The actual HTTP startup/outage/recovery exercise passes. Hosted GitHub CI is **UNVERIFIED**; workflow syntax and its commands were validated locally on Windows, not on a hosted Ubuntu runner.

The first full regression attempt passed 422 tests and failed one existing homonym test during fixture ingestion: a three-second connection-pool acquisition timeout occurred before its identity assertions. The failed XML and log are preserved, and regression_attempts.json records both attempts. The complete rerun used the same runtime, limits and assertions, with the unused Stage 6 container stopped to reduce resource pressure. The final counts above describe that complete passing rerun; the earlier failure is not discarded.

## Data and independence

There are **180 final questions**: 90 document-held-out and 90 template-held-out. Another 18 questions form a separate calibration set, giving 198 total questions. Final sets each have 64 positives and 26 unanswerable questions. They use 20 newly authored fictional worlds; two additional worlds are calibration. The combined isolated corpus contains **211 documents/chunks, 260 new stored canonical identities and 243 accepted source facts**. The source-derived registry has 287 entries, including 27 inherited reviewed identities that are not stored in this challenge graph. No standalone curated facts were loaded.

All 243 accepted facts passed independent source-provenance validation. Ingestion and indexing were repeated without duplicate publications. There were 48 sentence rejections: 44 non-asserted statements and four unsupported patterns. Other unfamiliar usage/hosting structures produced no relationship candidates. Thirty-four documents have no accepted facts. The builder reads sources only; it does not import gold IDs, expected answers or paths. Runtime files and configuration were frozen before final labels were materialized. Both scoring runs preserve every failure and match **594** non-timing mode/question comparisons (198 questions × three modes).

The identity audit records 271 repeated exact source mentions mapped to existing canonical entries. These are source-policy coalescences, not externally verified identity merges. There are zero inherited historical identities stored and zero duplicate canonical IDs; explicit employee-qualified homonyms remain distinct. Full source-span-to-registry candidate mappings are retained in identity_audit.json.

The author knew the scenario and template design. The local seal/access log is process discipline, not external custody. Document holdout tests new source identities with related grammar combinations; template holdout tests new productions. Repeated synthetic worlds are correlated. See STAGE6_EVALUATION_PROTOCOL.md and STAGE6_GENERALIZATION.md for the full Stage 5 exposure audit and limits.

## Quality

Historical Stage 5 used 92 source documents and the previously inspected 122-question benchmark:

| Historical mode | One hop | Two hops | Three hops | Full textual chain |
| --- | ---: | ---: | ---: | ---: |
| Vector | 97.22% | 25.00% | 4.17% | 46.88% |
| Graph | 100% | 100% | 100% | 100% |
| Hybrid | 100% | 100% | 100% | 100% |

The new challenge below is a different question/source distribution, not a before/after optimization. Document holdout also changes question forms from Stage 5; it does not isolate document novelty alone. In particular, vector's zero end-to-end accuracy is an answerer grammar finding, not proof that vector retrieval failed to find useful text.

| Mode | One hop (80) | Two hops (36) | Three hops (12) | Positive answers (128) |
| --- | ---: | ---: | ---: | ---: |
| Vector | 0/80 = 0.00% | 0/36 = 0.00% | 0/12 = 0.00% | 0.00% |
| Graph | 36/80 = 45.00% | 14/36 = 38.89% | 4/12 = 33.33% | 42.19% |
| Hybrid | 36/80 = 45.00% | 14/36 = 38.89% | 4/12 = 33.33% | 42.19% |

| Mode | Document-held-out positive accuracy | Template-held-out positive accuracy | Final overall accuracy including abstentions |
| --- | ---: | ---: | ---: |
| Vector | 0.00% | 0.00% | 28.89% |
| Graph | 84.38% | 0.00% | 58.89% |
| Hybrid | 84.38% | 0.00% | 58.89% |

| Mode | Required evidence recall | Full textual chain | Validated graph chain | False abstentions | Correct unanswerable abstentions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vector | 60.81% | 45.31% | N/A | 128/128 | 52/52 |
| Graph | 42.19% | 42.19% | 42.19% | 74/128 | 52/52 |
| Hybrid | 76.56% | 67.19% | 42.19% | 74/128 | 52/52 |

| Final category | Questions | Answerable | Vector exact match | Graph exact match | Hybrid exact match |
| --- | ---: | ---: | ---: | ---: | ---: |
| unanswerable | 52 | 0 | 100.00% | 100.00% | 100.00% |
| ambiguous | 20 | 0 | 100.00% | 100.00% | 100.00% |
| conflicting | 4 | 0 | 100.00% | 100.00% | 100.00% |
| paraphrased | 90 | 64 | 28.89% | 28.89% | 28.89% |
| multiple_answers | 8 | 8 | 0.00% | 50.00% | 50.00% |
| missing_evidence | 28 | 0 | 100.00% | 100.00% | 100.00% |

Category groups overlap and exact-match rates include correct abstentions. They must not be summed or called successful positive reasoning. In particular, template-held-out conflict/ambiguity cases reject grammar before testing contradictions or identity resolution.

Graph and hybrid return 54/128 positive answers. Their complete graph-proof coverage is 54/128. Graph has 88/88 correct citations; hybrid has 88/88. Vector has no answer citations, so citation correctness is N/A. All modes have **zero unsupported final answers, zero incorrect citations and zero source-invalid citations** at top_k=5 on this challenge. All correctly abstain on 52 unanswerable questions. This does not prove contradiction recognition when a question is rejected before interpretation. The historical vector k=1 partial-set failure is preserved.

Wrong-entity resolutions: graph 0/50 checked question starts, hybrid 0/50; vector exposes no canonical linker, so N/A. These are scoped checks, not a universal entity-resolution guarantee. Ambiguous names remain unresolved. Source construction contains all required accepted facts for 108/128 positives (84.38%). Missing extraction affects 20 positives across both final sets. Graph/hybrid primary failures are ten extraction failures in document holdout plus 64 unsupported query forms in template holdout; ten of those template questions also have extraction gaps. Vector's 128 false abstentions are attributed to its unsupported answerer grammar, even though retrieved text contains complete evidence for 58 questions.

Hybrid has zero uniquely correct positive answers, graph has zero uniquely correct positives versus hybrid, and vector has zero uniquely correct positives. Graph and hybrid jointly answer 54 positives that vector does not. Hybrid introduces no additional wrong answers here. It improves textual chain coverage through extra chunks but cannot turn unsupported question syntax or missing graph facts into final answers under its declared proof policy. Reranking/candidate discovery is not a general semantic question interpreter. For supported structured questions with extracted source evidence, graph-only remains the simpler measured choice. No universal mode preference is established.

## Warm performance

| Mode | Document-held-out p50/p95 ms | Template-held-out p50/p95 ms | All final questions p50/p95 ms |
| --- | ---: | ---: | ---: |
| Vector | 110.41 / 242.73 | 103.39 / 196.55 | 105.66 / 225.07 |
| Graph | 279.60 / 615.64 | 0.06 / 0.18 | 0.12 / 475.62 |
| Hybrid | 381.87 / 1102.76 | 105.87 / 195.57 | 131.36 / 691.43 |

The combined graph median is dominated by immediate unsupported-template abstentions. It is not an answered-query speed improvement. Document-held-out timings are more useful for the supported workload. Cold local model first encode took 17.94 seconds in the second scoring run; cached weights, no OS cache flush. Per-request phases and both runs remain in JSON. Sources, upfront discovery and final evidence budgets are not equalized across modes: top_k=5 limits vector candidates, not the graph's final evidence count.

## Fifty-user results

| Mode | Users | Requests | Answers | Correct abstentions | False abstentions | Errors | Explicit request-budget timeouts | p50/p95 ms | Completed requests/s | Correct results/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Graph | 50 | 100 | 27 | 24 | 0 | 49 | 0 | 2996.37 / 3927.97 | 11.11 | 5.67 |
| Vector | 50 | 100 | 25 | 24 | 51 | 0 | 0 | 3358.75 / 6545.64 | 7.40 | 3.63 |
| Hybrid | 50 | 100 | 66 | 20 | 0 | 14 | 0 | 10759.61 / 18997.96 | 2.76 | 2.37 |

These are short service-level bursts (100 requests/mode), not sustained HTTP or production capacity. Completed throughput includes errors and false abstentions. Correct-results throughput counts correct answers and correct abstentions. Pool-acquisition and driver read timeouts are included in database errors, not the explicit application-budget timeout column. A separate 50-request diagnostic observed 28 ConnectionAcquisitionTimeoutError causes. Host CPU reached 100%. Pool occupancy is N/A; configured maximum is ten. See STAGE6_PERFORMANCE.md for every level, query plans and embedding contention.

Hybrid had fewer database errors than graph in the 50-thread burst (14 versus 49), but its 100 requests took 36.28s rather than 9.00s. It delivered 2.37 correct results/s versus graph's 5.67. Its serialized embedding stage may stagger database demand; this is an inference, not a measured admission-control mechanism. This reliability difference does not create a uniquely correct challenge answer or establish better production capacity.

## Recovery

Neo4j became Bolt-ready **53.78 seconds** after the start command. After readiness, the first graph query with a loaded model took **19.24 seconds**. The subsequent vector and hybrid queries took 5.40 and 2.06 seconds. A fresh API/model hybrid query took **18.23 seconds**, including 15.77 seconds in model startup/embedding. These are sequential measurements, not exchangeable cold conditions.

The interrupted request failed safely. Database-unavailable queries returned 503 in all modes; liveness stayed 200 and readiness recovered to 200. Subsequent HTTP hybrid calls took 13.83s, 3.33s, 1.63s, 1.02s, 1.39s. Recovery remains variable; the earlier 20.02-second query cannot be attributed only to embedding or only to database startup. See STAGE6_RELIABILITY.md.

## Remaining limits

Finite extraction and question grammars, synthetic correlated cases, controlled identity assumptions, a 211-document corpus, strict global publication availability, different evidence budgets, pool pressure, embedding serialization and cold database/model behavior remain material limits. No final challenge tuning or performance optimization was made. No paid provider, remote repository, commit, push or deployment was used. **Work stops after Stage 6. Stage 7 is not started.**
