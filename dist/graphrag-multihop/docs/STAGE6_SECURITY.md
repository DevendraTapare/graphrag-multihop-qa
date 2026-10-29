# Stage 6 security and provenance checks

The challenge graph is built only from source documents in a separate Neo4j volume. Canonical identities come from the existing source discovery policy. Explicit employee-qualified homonyms remain distinct. Repeated full-name/org mentions can coalesce under the documented controlled identity policy; indistinguishable real-world homonyms remain a limitation. No gold entity IDs, expected paths or missing gold facts are loaded into the graph.

Runtime Cypher comes from allowlisted internal templates with parameterized entity values. Requests cannot supply Cypher or filesystem paths. Paths remain explicitly typed and limited to three relationships, 128 raw candidates and ten final answers. Structural provenance edges are not reasoning hops. Request validation rejects unbounded hop requests and invalid top_k values. Graph cycles cannot justify a shorter fabricated path.

Existing real integration regressions cover injection strings, identity ambiguity, conflicting hosting, deleted source/run/document references, tampered offsets/quotes/hash/processing versions, stale publications, invalid branches, candidate overflow, cycles, current source corrections, vector publication corruption and outage/recovery. The source-only publication seal runs before capture and again at revalidation. Every selected edge receives independent source proof. Removing that work to improve timing is outside this evaluation.

Stage 6 adds real cross-mode similar-name checks, idempotent ingestion concurrent with retrieval, and a held-out paraphrase test that preserves retrieved vector text while refusing unsupported final answers. Unit checks prevent runtime/build imports or file reads of challenge labels, preserve full non-timing reproducibility comparisons, and make CI reject skipped tests. Existing filesystem tests cover traversal, absolute/Windows paths, symlinks/junctions and disallowed files. The loader remains restricted to fictional local documents.

The actual HTTP outage exercise stops only the Stage 6 database after an in-flight graph request has completed a real path read and still needs proof. It must fail safely rather than return a partial path. All three HTTP modes must return safe 503 responses with request IDs while the database is unavailable. Liveness stays available, readiness recovers, and no vector-answer fallback is accepted as hybrid proof.

These checks apply to the tested cases. They do not prove universal resistance to arbitrary natural-language attacks, identity ambiguity or operating-system compromise. The challenge label access log records supplied script accesses; it is not an operating-system audit trail. Unsupported-answer and citation counts are reported from the actual final evaluation, even if they are nonzero. Hosted CI remains UNVERIFIED.

## Concrete regression coverage

| Risk | Concrete coverage |
| --- | --- |
| Cypher injection | `test_cypher_input_does_not_mutate_graph`; user captures remain parameter values |
| Unbounded hops/candidates | Strict GraphRequest/HybridRequest validation; `test_actual_queries_are_bounded_and_have_no_vector_search`; candidate-overflow tests |
| Cycles and fabricated paths | `test_cycles_do_not_expand_traversal`, `test_unsupported_direct_shortcut_is_not_reasoning`, `test_structural_links_cannot_replace_missing_facts` |
| Similar names/unsafe merges | `test_similar_name_distractor_does_not_cross_modes`, `test_source_discovered_homonyms_remain_distinct_in_database`, duplicate canonical-ID checks |
| Contradictory assertions | `test_conflicting_hosting_keeps_paths_and_abstains`; challenge conflicts distinguished from early grammar rejection |
| Stale sources | `test_corrected_source_excludes_old_relationship`, `test_current_correction_and_independent_source` |
| Tampered proof/deleted references | Parametrized `test_invalid_source_or_provenance_never_answers`, `test_bad_source_or_edge_cannot_support_hybrid`, publication-seal mutation tests |
| Concurrent write/read | `test_concurrent_source_change_returns_explicit_error`; new real idempotent-ingestion/read concurrency check |
| Outage/recovery | Existing real-driver outage tests plus the separately measured Compose/HTTP Stage 6 interruption and recovery |
| Incorrect citations | `test_all_citations_resolve_exact_original_text`; exact span/hash tampering tests; all 243 accepted challenge assertions independently checked |
| Unauthorized file access | Temporary-file tests reject absolute/traversal paths and oversize/invalid files. A separate actual Windows junction escape was created and rejected, plus three unauthorized paths. The symlink unit guard uses monkeypatch; real symbolic-link creation was not separately tested. Query requests accept no file parameter. |

No security-critical integration test is replaced by a mock or silent skip. The final test totals and any initial failed attempt are recorded separately.

The filesystem exercise used a fictional file outside the allowed loader root but still inside this workspace's cache. A real Windows junction under the root pointed to that file. The loader rejected it as `linked_source_not_allowed`. Traversal, an absolute path and a Windows system-style path were rejected before reading. `filesystem_validation.json` records these four additional manual checks separately from pytest totals. No protected OS file was read.


## Final verification

423 checks passed: 294 unit and 129 real Neo4j integration, no skips/errors/failures. All 412 earlier tests are preserved. All 243 challenge facts passed provenance validation. Final evaluation: zero unsupported answers, zero incorrect citations and zero invalid source spans. Graph/hybrid citations are 88/88 correct; vector citation correctness is N/A because it abstains on every final positive. The bounded load errors and real outage failures remain reported; they are not silently scored as safe successful answers.
