# Hybrid component ablations

Every configuration uses the same 122 questions, 92 source-document versions, pinned local MiniLM and Neo4j environment. No gold labels enter runtime. The final CSV and per-configuration JSON preserve quality and latency, including negative results. “Held-out” remains a descriptive split because it was inspected in earlier development.

| Configuration | Entity registry used for query linking | Graph proof | Evidence order |
| --- | --- | --- | --- |
| Vector only | No registry; frozen Stage 3 text implementation | No graph | Vector rank |
| Aligned graph only | Source-derived registry | Mandatory complete validated paths | Canonical deterministic order |
| Hybrid without entity expansion | Original 27 reviewed identities | Mandatory complete validated paths | RRF |
| Hybrid without graph reranking | Source-derived registry | Mandatory complete validated paths | Vector rank, then remaining graph evidence |
| Full hybrid, with entity expansion | Source-derived registry | Mandatory complete validated paths | RRF evidence/path order with canonical ties |

“Hybrid with entity expansion” is the full hybrid configuration, not a separate repeated treatment with another label. Removing expansion changes query linking only; provenance validation still uses the actual source-derived processing version. Removing reranking retains all source proof and changes presentation order, not graph-edge validity. Every configuration uses top_k=5 where applicable and max_hops=3.

The no-expansion hybrid deliberately has no vector-answer fallback. It may retrieve text that supports an answer, yet abstain because it cannot resolve the start into the required graph proof. This is the declared hybrid safety policy, not evidence that vector-only retrieval stopped working. Its textual chain-coverage score can therefore be positive while its validated graph-chain coverage and answer accuracy are zero.

Results are in `reports/stage5/ablation_results.csv`, `comparison.json`, `hybrid_no_expansion_metrics.json` and `hybrid_no_reranking_metrics.json`. The CSV includes per-hop accuracy, textual and validated chain coverage, evidence recall, citation correctness, abstention, unsupported counts, p50/p95 and accuracy differences from the newly aligned vector run. Full final measurements are summarized in [STAGE5_REPORT.md](STAGE5_REPORT.md).

The experiment separates two questions. First, does source-driven identity coverage enable graph retrieval where the frozen registry failed? Second, does adding vector evidence/reranking improve answers beyond complete graph proof on this corpus? Because the generator retains all required graph support and never lets rank invent a missing edge, reranking may change evidence order and latency without changing accuracy. Such a null result must remain visible. The same applies if full hybrid costs more than graph-only without improving its answers.

The comparison does not isolate a universal property of graphs: it includes source-derived identities, structured extraction, complete branch enumeration, a fixed grammar and bounded top-k text retrieval. Improvements on these synthetic repeated patterns are not a blind generalization estimate or proof that hybrid is preferable on arbitrary corpora.

## Final measured component effects

| Configuration | Answerable exact accuracy | Textual chain coverage | Graph-chain coverage | p50 / p95 ms, all questions |
| --- | ---: | ---: | ---: | ---: |
| Vector only | 46.88% | 46.88% | N/A | 91.91 / 243.93 |
| Graph only | 100% | 100% | 100% | 177.35 / 337.24 |
| Hybrid without expansion | 0% | 46.88% | 0% | 88.47 / 212.79 |
| Hybrid without reranking | 100% | 100% | 100% | 288.55 / 682.69 |
| Full hybrid, with expansion | 100% | 100% | 100% | 279.27 / 637.68 |

All configurations have zero unsupported final answers at the standard top_k=5 setting and correctly abstain on all 26 unanswerable cases. Citation correctness is 100% where citations exist; the no-expansion hybrid has zero citations and an N/A rate. Removing expansion loses 100 percentage points of hybrid answerable accuracy. Removing reranking changes no answerable accuracy. Full hybrid ties graph-only quality while adding about 101.92 ms to median latency in this run. The small timing difference between the two hybrid ranking configurations does not establish a robust speed improvement. The evidence and upfront processing budgets differ from the vector-only pipeline; these are complete-pipeline results, not an isolated ranking algorithm experiment.
