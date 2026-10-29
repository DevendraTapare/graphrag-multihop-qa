# Stage 5 coverage audit and implementation plan

This audit precedes every Stage 5 graph write. Stage 2–4 reports, schema/provenance/evaluation protocols, the 122-question format, original registry/extraction/proof/lifecycle code, graph retrieval and the 92 source documents were reviewed. Stage 3 and Stage 4 results will remain immutable. The historical graph is preserved and Stage 5 will use a separate local Neo4j Community container and volume, never a destructive reset of the existing database.

The precise mismatch is accepted graph coverage, not missing source documents. A: vector retrieval indexes 92 source snapshots (the original 16 plus 76 benchmark-extension documents). B: graph ingestion stores these same source snapshots, but only the original reviewed identities yield 38 accepted automatic assertions, alongside 30 independently curated assertions. The extension's intended identities are absent from the 27-entry registry. C: evaluation labels refer to 64 factual spans in the extension documents, all present as original text, but none represented by accepted historical graph assertions. All 96 answerable starting identities are unresolvable in the historical registry. The Stage 4 audit records 121 not_found and one ambiguous result across all 122 questions. Missing extraction/identity coverage must not be called a traversal-algorithm failure.

`reports/stage5/history_freeze.json` and `frozen_stage4.zip` preserve the exact Stage 1–4 code/configuration/results, including Stage 3/4 metrics. The historical graph SHA-256 is `449ea1c1703fcecf7a75f2445102d9de19a5b7c8624fd41985675ce154a57a63`. Offline coverage diagnostics will record exact source sets, missing references, ready source documents with zero facts, accepted/rejected facts, stale assertions, identity starts, and per-question classifications before/after alignment. Counts with zero opportunities will be N/A, not perfect scores.

Source-only construction plan:

1. Use `scripts.vector.corpus_documents()` for the unchanged versioned source snapshots. No source builder may import evaluation JSON, expected answers, gold paths or gold IDs.
2. Discover typed entity mentions from full positive, non-code sentences in the existing approved corporate grammar. Preserve original offsets and content hashes. Reuse exact reviewed identities where compatible; create deterministic source-context identities otherwise. Scope technology deployments by project, qualified people by explicit employee context, and homonyms by supported organization context. Do not add fuzzy aliases or collapse names by prefixes.
3. Feed the source-derived registry into the existing Stage 2 pipeline, deterministic extractor, independent provenance validator and lifecycle writer. Existing grammar already covers manages/leads, works-for/employed-by, uses/utilizes, belongs-to/owned-by, hosted-on/runs-on. No relationship expansion is justified merely by a gold-label miss. Unsupported statements remain rejected.
4. Build graph and vector index in the separate Stage 5 database from exactly the same document IDs/hashes, with the same 600/80 chunk options and pinned MiniLM model. Reuse frozen Stage 3 vector-only code. Different processing versions/chunk IDs are explicitly recorded; original source spans remain the grading reference. Verify every accepted source proof and idempotent reconstruction.
5. Keep Stage 4 runtime unchanged. Stage 5 graph selection distinguishes legitimate set-valued management/technology branches from contradictory functional assertions for the same subject. Independent managed projects may lead to several valid answers; a missing known branch or conflicting ownership/employment/hosting for one subject forces abstention. This policy is defined before scoring.
6. Hybrid retrieval records real vector evidence, exact canonical candidate matches, actual validated graph paths, and fused evidence separately. Use reciprocal-rank fusion for evidence ordering, never raw similarity plus rule confidence. Retain every required graph support. Require a complete valid graph chain for hybrid answers; vector text alone will not fill a missing edge. Unknown/ambiguous starts cannot be replaced by a nearby vector hit.
7. Compare frozen historical vector scores, a new unchanged vector run, aligned graph-only, and hybrid on all 122 questions. Ablate entity expansion and evidence reranking. Separate cold/warm timings and expose any negative result. Freeze runtime before primary scoring, then repeat evaluation and verify historical preservation, real database adversarial cases, API outage/recovery and all Stage 1–4 regressions.

Both splits were authored/inspected in earlier stages, and the current task explicitly requests inspection of the dataset. Split reporting remains useful, but Stage 5 cannot claim unbiased held-out generalization. Discovery/rules will be justified by source text and independent adversarial/calibration examples; they will not be repaired per held-out answer. No paid APIs, commits, publication, deployment or Stage 6 work are authorized.

## Measured alignment follow-up

The preceding audit/plan was created before the first Stage 5 graph write. After source-only construction, `reports/stage5/coverage_audit.json` records:

| Diagnostic | Before | After |
| --- | ---: | ---: |
| Vector-indexed document versions | 92 | 92 |
| Current graph-ingested document versions | 92 | 92 |
| Labeled source references missing from graph | 0 | 0 |
| Accepted automatic facts | 38 | 150 |
| Supported benchmark facts | 0/64 | 64/64 |
| Resolvable answerable starts | 0/96 | 96/96 |
| Resolvable starts across all questions | 0/122 | 108/122 |
| Unresolved/ambiguous starts | 122 | 14 |
| Documents with no supported facts | 77 | 1 |
| Rejected candidates of all kinds | 133 | 8 |
| Rejected relationship candidates | 2 | 2 |
| Excluded historical automatic assertions | 41 | 0 |
| Assertions invalidated by changed content hash | 0 | 0 |

The 64 positive labeled facts span 52 source documents. The remaining 14 unresolved starts are twelve deliberately unrecorded employment identities and two ambiguous bare names; none is an answerable failure. The source-only graph contains 111 new canonical identities and reuses 27 original identities. Eight rejections comprise two entity, two relationship and four non-asserted sentence decisions. All 150 accepted facts pass independent provenance verification; all 111 new identities are actually persisted. Controlled identity tests observe no incorrect merge incidents.

Before alignment, answerable failures are entity-resolution/extraction coverage gaps even though their documents exist. After alignment, every positive fact and start is covered; intentionally missing relationships remain absent and cause correct abstention. Unsupported grammar, provenance, traversal and generation diagnostics remain distinct in raw responses and evaluation error analysis. The 41 historical exclusions were processing/run history, not content-version changes. Isolated tests separately verify corrections, invalidation, incomplete publication, corrupt evidence and deleted root branches.

`coverage_audit.json` preserves every question's split, hop count, resolution, missing fact IDs, missing source references, classification and expected-unanswerable status before/after. Retrieval metrics and failed examples are separate from this source-coverage diagnosis. Historical Stage 4 scores remain unchanged.
