# Stage 6 evaluation protocol — controlled-challenge-v1

This is a NEW CONTROLLED CHALLENGE SET authored and run by Codex. It is not an independent external benchmark. The author knows the scenario design and question productions. Hashes and an access log enforce the local experiment sequence; they do not provide independent custody, cryptographic secrecy or an unbiased population sample.

The Stage 5 archive and SHA-256 inventory were created before Stage 6 edits. All historical reports, source fixtures, runtime code, grading code, dependencies and databases remain unchanged. README and the roadmap may receive current-status updates.

## Four distinct evaluations

A. Stage 5 is historical: 122 previously inspected questions, including 61 called calibration and 61 called held_out. Both sets were exposed during development. Its 100% graph score establishes coverage and correct bounded reasoning on this prepared corpus, not broad generalization. Source-driven identity discovery improved coverage after those questions had been seen. Even without importing answer keys, shared sentence/question patterns and author knowledge are contamination risks. Reranking did not improve answers.

B. Document-held-out challenge: 90 new questions about 10 newly authored fictional worlds. Their documents were absent from Stage 1–5 development. Documents enter the graph and vector index at evaluation preparation time; “held out” does not mean withholding documents from retrieval. Question productions use different combinations of plural nouns, verbs and inverse forms from the old dataset, but some belong to the same supported grammar family. This is a lexical/compositional transfer test, not a grammar-independent test.

C. Template-held-out challenge: 90 questions about 10 additional fictional worlds. These use new sentence productions such as imperative requests, possessives and tracing requests. They are not copied from runtime grammar. Their structures are authored before freezing; final instantiated questions and gold labels are materialized only after runtime/configuration freeze. New extraction structures occur in both final sets.

D. Robustness: explicit homonyms, similar names, multiple project branches, conflicting hosting claims, missing hosting/ownership, unrelated projects, negation and injected instructions appear in the challenge sources. Existing and new real integration tests exercise mutation, publication consistency, bounded paths and outages. A separate 18-question calibration set uses two disjoint worlds. No improvement/tuning is planned; calibration is descriptive. Calibration and final metrics are always separate.

Sources use seed 602910 and namespace stage6. The source generator writes documents and offline semantic authoring records. The graph builder reads only sources.json, uses existing source-only discovery and extraction, and writes registry/corpus manifests. It never imports the generator, semantic records, questions, gold paths or evaluation labels. Gold semantic authoring IDs are not canonical runtime entity/fact IDs. No missing relationship is filled in manually.

## Seal and access rules

1. Preserve 241 existing files and both historical graph snapshots.
2. Generate sources without materializing labels; build/index and validate every accepted assertion in a separate database (127.0.0.1:27689, own volume).
3. Record SHA-256 hashes of all app code, source/build/runtime/evaluation scripts, source/runtime manifests, this protocol and uv.lock in configuration_freeze.json.
4. Only then materialize final labels. Record production, every label read and evaluation run in append-only label_access.jsonl. The offline world file is a known authoring record, not a hidden runtime input. No human-readable final question/label inspection occurs before freeze.
5. Verify frozen hashes before scoring. Preserve run1 and run2 separately, including every full response/failure. Never repair individual final questions or runtime behavior after scoring. If an evaluation defect needs repair, preserve the original run and disclose a new protocol revision; do not silently replace it.

This audit covers accesses through the supplied scripts and disclosed author review. It cannot detect an arbitrary uninstrumented operating-system read. An external evaluator should hold the question/label files in a separate account/process and deliver them only after independently checking the runtime hash. The supplied mechanism supports that separation but this local execution is not external validation.

## Fixed retrieval and grading

All modes receive exactly the same source versions and query strings. Vector top_k=5, graph max_hops=3, maximum 128 raw path candidates, maximum 10 final answers. Pinned local CPU MiniLM, no paid calls and no runtime network inference. Original deterministic Stage 3 normalized complete-set exact matching and exact citation spans are used unchanged. Graph and hybrid retain the Stage 5 source publication seal and full per-edge proof. Hybrid final answers require complete graph evidence; vector candidates are diagnostic only.

Report accuracy separately from source construction coverage, textual evidence coverage and validated graph paths. Gold answerability is determined by the source semantics, not by whether the extractor supports its wording. Contradictions, ambiguous identities and missing necessary branches require abstention. Complete answer sets include every supported project/technology. A multiple-project portfolio with an owner missing for one known branch must abstain. Unanswerable questions are not counted as successful positive retrieval.

Citation correctness requires the exact required source span to be grounded in a returned chunk. Also report source-span validity independently: an irrelevant but real citation is not correct task evidence. Unsupported answers use the unchanged strict grader: a non-null answer must be exact and have all required citations. It can therefore flag a partially supported or wrong answer, not only an invented sentence. Zero citations have N/A correctness. Full-chain textual coverage does not imply a validated graph chain.

Results are separated by set, hop count and overlapping tags. Primary failure causes distinguish unsupported query grammar, missing/ambiguous identities, extraction gaps, missing intermediate evidence, contradictions, provenance/path failure, insufficient vector evidence and answerer limitations. All raw examples remain available. No confidence interval or production generalization claim is justified by repeated synthetic worlds with correlated questions.

## Timing and reliability

Measure a fresh model process separately with cached local weights; no OS cache flush. Warm the model and each mode before sequential scoring. Repeat all scored questions and compare every non-timing field, ignoring request IDs and latency fields only. Record hardware, versions, source hashes, processing/index builds and dependency lock hash.

Bounded load uses one closed-loop request per simulated user at 1, 5, 10, 25 and 50 threads, two rounds each, separately per mode. Mix supported one-/two-/three-hop requests and a correct abstention; choose only calibration probes for load/recovery. Record actual outcomes, wall latency including queue time, throughput, errors/timeouts, instrumentation of database call time/count, embedding lock-inclusive time and resource samples. These are short service-level bursts, not a long-running HTTP capacity test. Pool size is configuration; internal utilization is N/A unless measured through a supported interface. Do not infer utilization from worker count.

Actual HTTP startup/readiness, safe errors, database stop/restart during a coordinated in-flight request, recovery, fresh model and warm-model connection reuse are measured separately. Driver read retries remain zero; ingestion managed retry maximum is 3 seconds; graph query timeout is bounded by remaining request budget. Application budgets are checked between calls and are not a hard operating-system cancellation deadline. Official driver controls: [query manual](https://neo4j.com/docs/python-manual/current/query-simple/) and [driver API](https://neo4j.com/docs/api/python-driver/current/api.html).

Inspect actual PROFILE plans for calibration paths, including round-trip counts, bounded typed relationships, indexed starts and publication/provenance overhead. Optimize only after measured evidence; this evaluation intentionally preserves the old runtime to make the transfer comparison clear. Hosted GitHub Actions remains UNVERIFIED until a real hosted run, and no remote repository is created.
