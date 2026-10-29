# Project roadmap

Stages 1–4 provide the local graph, automatic ingestion/provenance, frozen MiniLM vector baseline and bounded graph retrieval. Stage 5 adds source-driven discovery, an isolated shared corpus, graph backfill, hybrid evidence fusion and a measured three-way comparison with ablations.

The next stages require a separate request and design review. They are not started automatically.

| Proposed stage | Main work | Evidence needed before claiming success |
| --- | --- | --- |
| 2: ingestion and entity resolution (implemented) | Versioned sources, controlled grammar, reviewed aliases, gated publication, local CLI | See Stage 2 report for actual checks, precision/recall, and limitations |
| 3: vector baseline (implemented) | Local MiniLM, versioned Neo4j cosine index, text-only answers and API | See Stage 3 report and reports/stage3 for real checks, quality, performance, and limitations |
| 4: graph-only retrieval (implemented) | Bounded one-/two-/three-hop traversal, canonical identity, provenance, deterministic path answers | See Stage 4 report: working original-domain paths, zero benchmark answerable accuracy due to frozen upstream coverage, safe abstention, measured latency |
| 5: corpus alignment and hybrid GraphRAG (implemented) | Source-only registry discovery, isolated 92-document backfill/index, sealed publication, three retrieval modes and ablations | See Stage 5 report: 150 sourced facts, 100% aligned graph/hybrid accuracy on the inspected benchmark, zero unsupported answers, no hybrid accuracy gain over graph-only |
| 6: independent evaluation, robustness and performance | New controlled document/template challenges, frozen configuration, source-only isolated build, all three modes, bounded load and outage measurements | See Stage 6 report for actual results and conditional generalization limits; hosted GitHub CI remains UNVERIFIED |

The Neo4j GraphRAG Python package, LangGraph or an optional model provider still needs a concrete use case. Paid APIs, deployments, GitHub publication, commits and pushes are outside the authorized work. Historical Stage 1–5 results remain preserved. Work stops after Stage 6; Stage 7 is not started.

Stage 6 verdict: **CONDITIONAL**. Its new controlled challenge has 180 final questions plus 18 calibration questions, 211 source documents and 243 accepted facts. Graph and hybrid answer 54/128 final positives; all modes fail the new question-template positives. Hybrid adds evidence without a unique correct challenge answer. The final full rerun passes 423 tests, while the initial fixture-ingestion timeout and bounded-load errors remain preserved. See the [Stage 6 report](STAGE6_REPORT.md), [generalization audit](STAGE6_GENERALIZATION.md), [performance](STAGE6_PERFORMANCE.md) and [reliability](STAGE6_RELIABILITY.md). This is not an external independent benchmark; hosted CI is UNVERIFIED.

Stage 4's frozen graph result remains 0% at every hop count. Stage 5 fixes source representation coverage through document-only discovery: aligned graph-only and hybrid reach 100% at each hop, while the unchanged vector run retains 97.22%/25.00%/4.17%. The gain includes upstream identity/extraction coverage and complete structured traversal; it is not an unbiased generalization estimate. Hybrid adds latency without improving graph-only accuracy here. Further claims need independently unseen source/questions, broader grammars and stronger deployment/load evidence. See [Stage 5 evaluation](SHARED_CORPUS_EVALUATION.md).
