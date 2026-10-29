# Shared-corpus three-way evaluation

Stage 5 compares the unchanged Stage 3 vector-only implementation, aligned graph-only retrieval, and hybrid retrieval on the same 92 document snapshots. The source corpus is unchanged; new source-derived canonical identities and graph extraction make its previously unavailable relationships usable. This is a comparison of complete pipelines, including their representations and identity handling, not a claim that graph traversal alone explains every difference.

## Corpus and grading

The source set contains the original 16 documents plus 76 synthetic extension documents. Both aligned modes store/index the same 92 original document IDs and content hashes with 92 chunks. Chunk options remain 600 characters with 80 overlap. Registry expansion changes the ingestion processing version and therefore chunk IDs, but not source text, document identity, offsets or source versions. All 150 graph assertions come from the validated automatic pipeline; standalone curated relationships were not added to the aligned database. The old database remains untouched.

The benchmark remains `multihop-vector-v1`: 36 one-hop, 36 two-hop, 24 three-hop, and 26 unanswerable questions. Calibration and held-out splits each contain 61 questions (48 answerable). The historical disclosure remains in every metric file: both splits were authored/inspected during earlier development. These are descriptive split results, not a blind generalization test. Extraction uses source text only. Runtime never reads the evaluation file or expected answers/paths.

The unchanged `app/evaluation/baseline.py` grades exact normalized answer sets, original source spans, document recall, complete textual chains, citations and unsupported answers. Every required branch/fact must be present. Graph citation IDs are native automatic source IDs; no curated-to-automatic mapping is needed in Stage 5. Hybrid evidence normalization unions vector and graph chunks by `(document_id, chunk_id)` in actual fused order, retaining all required graph support. Quotes and Unicode offsets are unchanged. Duplicate references to the same chunk are collapsed without inventing support.

The top_k=5 limit applies to vector candidates. Graph expansion and final fused evidence may exceed five chunks; returned evidence/token budgets therefore differ between modes. Per-request latency excludes offline discovery, extraction, backfill and indexing. The experiment measures the complete prepared pipelines rather than equalizing their preprocessing or final evidence budgets.

A separate validated graph-chain metric requires actual returned complete path steps with matching relation type and exact source spans. Textual chain coverage alone is not called graph proof. On the no-expansion hybrid, retrieved text can contain a chain while the final answer correctly abstains under the mandatory graph-proof policy. Zero-citation correctness is N/A, never a perfect score.

## Results

| Measure | Frozen historical vector k=5 | New aligned vector k=5 | Aligned graph-only | Full hybrid |
| --- | ---: | ---: | ---: | ---: |
| One-hop accuracy | 97.22% | 97.22% | 100% | 100% |
| Two-hop accuracy | 25.00% | 25.00% | 100% | 100% |
| Three-hop accuracy | 4.17% | 4.17% | 100% | 100% |
| Answerable accuracy | 45/96 = 46.88% | 45/96 = 46.88% | 96/96 = 100% | 96/96 = 100% |
| All-question accuracy, including correct abstentions | 71/122 = 58.20% | 71/122 = 58.20% | 122/122 = 100% | 122/122 = 100% |
| Required-evidence recall | 68.23% | 68.23% | 100% | 100% |
| Complete textual chain coverage | 46.88% | 46.88% | 100% | 100% |
| Validated graph-chain coverage | N/A | N/A | 100% | 100% |
| Citation correctness | 57/57 = 100% | 57/57 = 100% | 191/191 = 100% | 191/191 = 100% |
| Answerable abstention | 53.13% | 53.13% | 0% | 0% |
| Correct unanswerable abstention | 26/26 = 100% | 26/26 = 100% | 26/26 = 100% | 26/26 = 100% |
| Unsupported answers | 0 | 0 | 0 | 0 |

Graph-only/full hybrid improve one-/two-/three-hop accuracy by **2.78 / 75.00 / 95.83 percentage points** over the aligned vector run. Answerable accuracy and complete-chain coverage improve by **53.125 points**, while evidence recall improves by **31.7708 points**. Graph-only and hybrid tie on every question category in this benchmark. The category table in `comparison.json`/each mode's `by_question_type` includes all tags, including overlapping tags, rather than selecting favorable examples. Both splits achieve 48/48 answerable graph/hybrid answers and 13/13 correct abstentions; their separate rows remain in JSON.

| Question tag (overlapping groups) | Questions | Aligned vector accuracy | Graph accuracy | Hybrid accuracy |
| --- | ---: | ---: | ---: | ---: |
| direct | 84 | 52.38% | 100% | 100% |
| entity_disambiguation | 2 | 100% | 100% | 100% |
| missing_intermediate | 12 | 100% | 100% | 100% |
| multi_intermediate | 8 | 37.50% | 100% | 100% |
| no_employment_evidence | 12 | 100% | 100% | 100% |
| paraphrase | 12 | 8.33% | 100% | 100% |
| single_intermediate | 88 | 47.73% | 100% | 100% |
| synthetic (all questions) | 122 | 58.20% | 100% | 100% |

Tags that describe unanswerable cases score correct abstentions. They are not additional answered positives. Groups overlap and must not be summed.

Source-only registry coverage rose from 27 to 138 identities (111 new; 27 reused in the new instance). Every answerable start resolves (96/96). Overall, 108/122 starts resolve; 12 deliberately absent people remain not_found and two unqualified homonyms remain ambiguous. All 64 labeled factual spans now have accepted graph assertions, versus zero historically. Documents with no supported facts fall from 77 to one. Missing source references remain zero. These changes explain why Stage 4's 0% graph result cannot be treated as a traversal failure.

The aligned graph's 150 assertions include all accepted source facts, not just the benchmark's 64 labels: 38 original automatic assertions and 112 extension assertions, including grounded archive and incomplete-sandbox statements. Missing sandbox USES edges remain absent because the documents never state them. The source-only registry/graph was not repaired using labels. Eight candidates remain rejected: two entity, two relationship and four sentence decisions. The observed merge tests report zero incorrect incidents within their controlled cases, not a universal identity guarantee.

## Latency and execution conditions

Final repeated-run p50/p95 end-to-end service latency over all 122 questions:

| Mode | p50 ms | p95 ms |
| --- | ---: | ---: |
| Frozen historical vector k=5 | 87.18 | 217.92 |
| New aligned vector | 91.91 | 243.93 |
| Aligned graph-only | 177.35 | 337.24 |
| Full hybrid | 279.27 | 637.68 |
| Hybrid without expansion | 88.47 | 212.79 |
| Hybrid without reranking | 288.55 | 682.69 |

Measurements use Windows 11, Python 3.12.13, Neo4j Community 5.26.32, one physical/logical CPU and approximately 14.9 GB host RAM. MiniLM remains the pinned 384-dimensional normalized CPU model with two inference threads. The aligned cosine index is ONLINE. Main runs are sequential at concurrency one, top_k=5 and max_hops=3. The isolated Stage 5 instance runs alongside the idle preserved historical instance; the new index/build and processing metadata differ from Stage 3. No database tests or outage exercise overlap the measured workloads. OS scheduling, caches and index ties limit exact latency comparisons.

The model starts in a new process using cached local weights. Its startup/first inference is measured separately, followed by explicit original-domain warm-up requests. No OS cache eviction is performed. `performance.json` records startup and first requests; `determinism.json` retains the first/second full timing distributions. The actual HTTP check also restarts the isolated database and records recovered-request timing, a different cold condition from a fresh model process. Concurrent HTTP results are a separate small workload and cannot establish production capacity.

Per-request JSON retains parsing, embedding, vector search, candidate generation, linking, graph traversal, provenance, revalidation, fusion, answer generation and total timing. The graph capture/revalidation phases include the bounded source-publication seal, not only path matching. The seal deliberately adds work to detect hidden deleted branches. Graph-only's higher accuracy comes with greater latency than the unchanged vector baseline here. Full hybrid adds vector/candidate/fusion work without improving graph-only's already complete answers. Minor differences between hybrid reranking configurations are local timing variation, not evidence of a robust speed advantage.

## Reproducibility and limitations

The final runtime was frozen before two final scoring runs. An earlier development run was superseded by a source-publication integrity check and stricter candidate boundaries; its summary/freeze remain available. Final repeated scoring compares all non-timing per-question fields, including vector scores, source IDs, paths, citations and fusion order: 610 comparisons across five configurations. Historical Stage 3/4 metrics and graph snapshot are checked independently and never overwritten. Every failure/abstention remains in `reports/stage5/error_analysis.md` and the full query rows.

```powershell
uv run python -m scripts.coverage_stage5
uv run python -m scripts.verify_aligned
uv run python -m scripts.evaluate_stage5
```

The fixture grammar and small, previously inspected synthetic dataset make 100% attainable without broad natural-language competence. The registry/extractor representation differs from the text-only baseline, and vector top_k=5 limits its retrieved evidence. This experiment supports a graph coverage/navigation benefit under these conditions. It does not show that hybrid improves on complete graph-only retrieval, or that graphs universally outperform vector search. Missing/ambiguous source identity, unsupported grammar, larger corpora, publication failures and concurrency still require conservative failure or further evaluation.

The frozen vector answerer also retains its historical Stage 3 top_k=1 partial-set failure (one unsupported answer under the strict complete-set grader). Stage 5 does not alter or conceal that baseline. Reported zero unsupported counts here apply to the standard top_k=5 comparison and listed tests, not an all-k or arbitrary-corpus guarantee. Hybrid does not accept a vector candidate in place of complete graph proof.
