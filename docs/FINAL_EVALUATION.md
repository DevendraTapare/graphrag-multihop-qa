# Final portfolio evaluation

These are controlled fictional-data experiments. Answer generation is deterministic; no paid generative LLM was evaluated. A correct abstention is scored separately from answering an answerable question. Overall scores that include negatives must not be mistaken for positive-question accuracy. Historical reports remain in `reports/`; this account preserves failures as well as successes.

## Stage 1–2 foundations

Stage 1 established 30 curated factual assertions with explicit source fixtures and passed 78 tests. Stage 2 processed 16 source documents into 38 accepted automatic facts and passed 180 tests. Its separate 53-document extraction evaluation had 110/110 correct entity examples (100%), 30/30 accepted relationships correct (100% precision) and 30/32 positive relationships recovered (93.75% recall). Two unsupported relation forms remained false negatives. The Stage 2 held-out split was inspected while fixing a prefix bug, so it is not a blind independent estimate. These earlier checks establish the fictional pipeline's foundation, not open-domain extraction quality; their detailed reports remain in the package.

## Stage 3 baseline and Stage 4 mismatch

Stage 3 evaluated 122 questions: 96 answerable (36 one-hop, 36 two-hop, 24 three-hop) and 26 unanswerable. At top-k 5 the vector baseline answered 35/36 one-hop (97.2222%), 9/36 two-hop (25%) and 1/24 three-hop (4.1667%). Positive accuracy was 45/96 (46.875%). With 26/26 correct negative abstentions, overall correctness was 71/122 (58.1967%). False abstentions were 51/96 (53.125%). Complete text-chain coverage was 45/96 (46.875%), and mean required-evidence recall was 68.2292% across 96 positives. Emitted citations passed 57/57 checks (100%); unsupported answers were zero in this top-k 5 comparison. A known top-k 1 partial-answer counterexample remains documented and is not erased by that result.

Stage 4 ran graph retrieval against a different graph corpus. All 96 answerable question starts were unregistered, and 64 required gold facts were absent. All positive hop scores were zero: 0/36, 0/36 and 0/24; false abstentions were 96/96. No citations were emitted, so citation precision is N/A. This showed corpus and identity coverage failure, not evidence that a correctly populated graph could not traverse three hops. The original qualified Priya three-hop fixture worked separately.

## Stage 5 aligned, inspected corpus

After source alignment, the graph held 92 source documents/chunks, 138 registry identities (111 newly discovered and 27 reused) and 150 automatically supported facts. All 96 answerable starts resolved. Both 61-question splits and their labels had already been inspected; these were development comparisons, not an independent generalization result.

| Mode | One hop /36 | Two hops /36 | Three hops /24 | Correct positives /96 | Complete text chains /96 | Validated graph chains /96 | False abstentions /96 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Vector, k=5 | 35 (97.22%) | 9 (25%) | 1 (4.17%) | 45 (46.875%) | 45 (46.875%) | N/A | 51 (53.125%) |
| Graph | 36 (100%) | 36 (100%) | 24 (100%) | 96 (100%) | 96 (100%) | 96 (100%) | 0 (0%) |
| Hybrid | 36 (100%) | 36 (100%) | 24 (100%) | 96 (100%) | 96 (100%) | 96 (100%) | 0 (0%) |

Each mode correctly abstained on 26/26 negatives. Graph and hybrid emitted 191/191 valid source citations each; vector emitted 57/57. Unsupported answers were zero for these k=5 settings. Graph/hybrid overall correctness was 122/122; vector 71/122. Removing entity expansion reduced positive correctness to 0/96, while removing reciprocal rank reranking did not change final answers. Five configurations yielded 610 deterministic repeated comparisons. Hybrid's 100% was not a gain over graph's 100% on this inspected set.

## Stage 6 controlled challenge

The new challenge has 198 questions: 18 calibration questions and **180 final questions**. Final scoring excludes calibration. There are 90 document-holdout and 90 template-holdout questions, each with 64 positives and 26 negatives. Together: 128 positives (80 one-hop, 36 two-hop, 12 three-hop) and 52 negatives. The source publication has 211 documents, 260 new stored identities and 243 accepted source-backed facts. All 243 accepted facts passed provenance checks; this is accepted-fact validation, not extraction recall.

| Mode | One hop /80 | Two hops /36 | Three hops /12 | Correct positives /128 | Complete text chains /128 | Validated graph chains /128 | False abstentions /128 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Vector, k=5 | 0 (0%) | 0 (0%) | 0 (0%) | 0 (0%) | 58 (45.3125%) | N/A | 128 (100%) |
| Graph | 36 (45%) | 14 (38.8889%) | 4 (33.3333%) | 54 (42.1875%) | 54 (42.1875%) | 54 (42.1875%) | 74 (57.8125%) |
| Hybrid | 36 (45%) | 14 (38.8889%) | 4 (33.3333%) | 54 (42.1875%) | 86 (67.1875%) | 54 (42.1875%) | 74 (57.8125%) |

Required-evidence recall averages across the 128 positive questions: vector 60.8073%, graph 42.1875%, hybrid 76.5625%. Text-chain coverage requires the complete gold text evidence set. Validated graph-chain coverage additionally requires an actual accepted graph path. These measures are not interchangeable with answer accuracy.

All modes correctly abstained on 52/52 final negatives (100%). Overall correctness was vector 52/180 (28.8889%) and graph/hybrid 106/180 (58.8889%). There were no unsupported answers in these evaluated final outputs. Graph and hybrid citations passed 88/88 source checks each (100%); vector emitted zero, so its citation precision is N/A. Incorrect source/task citations were zero in the checked outputs. Wrong-entity answers were 0/50 checked start resolutions for graph and hybrid; vector start-resolution precision is N/A. There were no hybrid-only or graph-only correct positives: all 54 wins over vector were shared.

Within the document-holdout positives, graph and hybrid answered 54/64 (84.375%); vector 0/64. Within template-holdout positives, every mode answered 0/64. The frozen vector answerer lacks the new plural question forms; its zero answer score does not mean its embeddings retrieved zero useful evidence. New extraction forms also left 20/128 final positives without complete graphs. Only 108/128 (84.375%) had complete constructed gold chains. The document split also changes phrasing, so it is not a clean source-only causal experiment.

There were 20 bare-homonym negatives and four contradiction negatives. Every mode abstained, but half of each group belongs to unsupported template forms and may reject before resolving identity or inspecting conflict. Those successes do not establish general contradiction detection or identity robustness.

## Independence, confidence and reproduction

Runtime code/configuration was frozen across 75 paths before new labels were created. Label access and source novelty were audited; new source IDs and identity names had zero overlap, and normalized question templates had zero exact overlap with earlier questions under that audit's normalization. Grammar families still overlap. The same author controlled source generation, labels, protocol and runtime, and the runtime author could inspect labels after creation. This is controlled internal holdout evidence, not an externally administered blind benchmark. There is no natural-document or open-domain validation.

Two runs matched on 594/594 non-timing comparisons (198 questions × three modes). Deterministic repetition establishes repeatability on these cases, not independent sampling confidence or population accuracy. Questions share generated worlds, facts and templates; naive binomial confidence intervals would imply independence that this design does not support. Twelve three-hop positives are especially weak support for a broad accuracy claim. No statistical superiority or universal graph advantage is claimed.

The clean release retains the fictional datasets, label files for offline evaluation, primary result rows and ablation summaries. The safe portfolio runner can rebuild the source-only challenge and evaluate all 198 questions; the Stage 7A executed smoke is a separate nine-question subset, not a rerun of the 180-question score. Legacy research recorders may expect excluded private snapshots/archives and can overwrite their own report outputs; they are retained for inspection and should not be used as the clean reproduction entrypoint. Use [DEMO_GUIDE.md](DEMO_GUIDE.md).

## Latency and reliability limits

Stage 3 warm vector end-to-end p50/p95 was 87.18/217.92 ms; cold model startup was 15.79 seconds. Stage 5 warm vector, graph and hybrid p50/p95 was 91.91/243.93, 177.35/337.24 and 279.27/637.68 ms respectively. Stage 6 final mixed questions gave vector 105.66/225.07 ms, graph 0.12/475.62 ms and hybrid 131.36/691.43 ms. The tiny graph median includes immediate unsupported-grammar rejection. On document-holdout questions alone, graph p50/p95 was 279.60/615.64 ms and hybrid 381.87/1102.76 ms. These different mixtures are not controlled speedup comparisons.

The original 50-user, 100-request bursts produced 0 vector, 49 graph and 14 hybrid errors. Original p95 was 6.55, 3.93 and 19.00 seconds respectively. Completed requests/s included errors: 7.40, 11.11 and 2.76. A short latency caused by erroring early is not useful work. Stage 7A repeats and the pool correction are recorded in [ENGINEERING_DECISIONS.md](ENGINEERING_DECISIONS.md) and [STAGE7A_RELEASE_REPORT.md](STAGE7A_RELEASE_REPORT.md).

Historical restart readiness took 53.78 seconds, and the first graph query after restart took 19.24 seconds. A fresh API/model hybrid request took 18.23 seconds including 15.77 seconds of embedding startup. An in-flight database stop returned a safe error after 8.01 seconds; all three HTTP retrieval routes returned 503 during outage, liveness stayed 200 and readiness changed from 503 to 200 after recovery. These are bounded local observations. Hosted CI, sustained HTTP capacity, external deployment, hard deadline cancellation and production availability remain unverified.
