# Generalization and the Stage 5 evidence audit

Stage 5's 100% graph score is a controlled coverage result. It is not evidence that the system understands arbitrary questions or documents.

The historical evaluation has 122 questions: 96 answerable and 26 unanswerable. Its 61 calibration and 61 held_out questions had both been inspected in earlier development. The Stage 5 report, coverage audit, shared-corpus comparison, ablations and all three raw metric files disclose this. The calibration split has 48 answerable and 13 unanswerable questions; the nominal held-out split has the same composition. Neither split is a new blind test.

The runtime does not read the answer keys. The unchanged Stage 3 grader reads gold answers, required fact IDs, document IDs, quotes and offsets only in offline evaluation. `scripts.evaluate_stage5.normalize` unions actual graph/vector chunks; it does not inject gold evidence. `graph_chain` checks actual returned path steps against the offline labels. Exact-match grading requires the complete normalized answer set. Citation correctness requires exact task-relevant source spans, not merely a plausible-looking document name.

The graph was backfilled from `scripts.vector.corpus_documents()`: the original fictional source documents, local text/Markdown and the Stage 3 source corpus. `app.aligned.discovery.discover` prepares a typed registry from positive source sentences; the existing extraction/provenance pipeline separately accepts or rejects facts. The 111 new identities came from those documents. Runtime source manifests contain accepted source assertion IDs and endpoints for publication consistency, not expected question paths. They are used to reject damaged publications, not answer questions from a stored solution.

That separation prevents direct label import. It does not eliminate development contamination. The same author could inspect questions and sources, and the expanded registry and extraction representation were developed after the benchmark had been seen. Most documents and questions repeat a few matching grammar families. Explicit management, database usage and hosting statements align closely with the closed path interpreter. Synthetic scoped names simplify identity resolution. The deterministic complete-set answerer is evaluated on its intended task types. These conditions make the 100% score easier to attain.

Stage 5's initial development run was superseded by stricter publication and candidate-boundary checks after review. Its initial freeze and development summary were retained. Two final runs then matched 610 non-timing comparisons. This demonstrates repeatability of the final configuration on that dataset; repeatability does not create a fresh test split.

The vector comparison uses the same source versions and real local embeddings. It also uses a finite text answerer and a five-chunk retrieval cap. Graph expansion can return more than five support chunks and benefits from offline source discovery/extraction. These are comparisons of complete prepared pipelines with different preprocessing and final evidence budgets. Hybrid ties graph-only because its final answer still requires the same complete graph proof. Reranking changes evidence order, not which facts are accepted. The known vector k=1 partial-set failure remains preserved.

Stage 6 retains the existing runtime and grader. New source documents introduce unseen identities, paraphrased statements, conflicts, similar names, missing evidence and multiple branches. Document-held-out and template-held-out sets are reported separately. The final instantiated questions and labels are created only after configuration freeze; there is no final-question tuning. The author knows the design, so the correct label remains NEW CONTROLLED CHALLENGE SET.

See the [protocol](STAGE6_EVALUATION_PROTOCOL.md) for the local seal, label access limits and external-custody procedure. All failures remain in `reports/stage6/error_analysis.md` and both complete scored runs. Accuracy on supported/extracted questions must be separated from end-to-end accuracy on the full source semantics. Missing extraction patterns are corpus construction gaps; unsupported question forms are interpretation gaps. Neither should be called a successful answer because the system safely abstains.


## Final measured challenge results

| Mode | Document-held-out positive accuracy | Template-held-out positive accuracy | Final overall accuracy including abstentions |
| --- | ---: | ---: | ---: |
| Vector | 0.00% | 0.00% | 28.89% |
| Graph | 84.38% | 0.00% | 58.89% |
| Hybrid | 84.38% | 0.00% | 58.89% |

| Mode | One hop (80) | Two hops (36) | Three hops (12) | Positive answers (128) |
| --- | ---: | ---: | ---: | ---: |
| Vector | 0/80 = 0.00% | 0/36 = 0.00% | 0/12 = 0.00% | 0.00% |
| Graph | 36/80 = 45.00% | 14/36 = 38.89% | 4/12 = 33.33% | 42.19% |
| Hybrid | 36/80 = 45.00% | 14/36 = 38.89% | 4/12 = 33.33% | 42.19% |

| Mode | Required evidence recall | Full textual chain | Validated graph chain | False abstentions | Correct unanswerable abstentions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vector | 60.81% | 45.31% | N/A | 128/128 | 52/52 |
| Graph | 42.19% | 42.19% | 42.19% | 74/128 | 52/52 |
| Hybrid | 76.56% | 67.19% | 42.19% | 74/128 | 52/52 |

The document-held-out set loses ten positive answers through extraction gaps. The template-held-out set loses all 64 positives through unsupported interpretation. Unfamiliar statements include responsibility resting with a person, a project relying on a database, and a platform providing hosting. None is added manually to the graph. Twelve source-level semantic statements across four final worlds are unextracted; these affect twenty final positive questions. Source construction fully covers 108/128 positives, while the query interpreter still blocks template-held-out questions.

Vector retrieves complete text evidence for 58/128 positives but its answerer rejects every new question form. Hybrid text covers 86/128 complete chains, yet it produces the same 54 positive answers as graph-only. This demonstrates why evidence coverage, answerer coverage and final accuracy must be separate. A safe grammar rejection is a false abstention on an answerable question.

All four final contradiction questions receive abstentions. Only the two document-held-out cases actually reach conflicting graph facts; template-held-out cases reject syntax first. The twenty final bare-homonym questions also abstain; unsupported grammar explains the template half. These should not be counted as twenty successful disambiguations or four successful contradiction detections. Graph and hybrid resolve zero wrong entities in fifty checked explicit starts; vector has no canonical resolution metric. Similar-name identity checks also pass in real integration tests.

The primary failure inventory preserves every failed/abstained row and runtime reason. No before/after quality improvement is claimed because runtime/configuration was not tuned. Hybrid-only, graph-only-exclusive and vector-only-exclusive positive wins are all zero; graph/hybrid jointly outperform vector on 54 positives. New sentence interpretation or semantic candidate linking would need new calibration work and another sealed evaluation, not final-question patches.
