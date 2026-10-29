# Baseline evaluation protocol

`data/evaluation/baseline_v1.json` fixes dataset version `multihop-vector-v1`. It contains 122 fictional questions: 36 one-hop, 36 two-hop, 24 three-hop, and 26 unanswerable. Every answerable case has an explicit expected answer, required source snapshots, supporting exact-span fact labels, hop count, and one or more ordered evidence chains. A multi-intermediate answer requires the union of its chains. Gold authoring never calls extraction, retrieval, or generation.

The benchmark adds 76 small synthetic documents to the existing 16-document corpus. Calibration and held-out scenarios use different people, organizations, project names, question surfaces, and document layouts. Similar names, qualified homonyms, distractor archives, missing intermediate uses statements, and multiple projects for one manager test common evidence failures. Calibration separates most facts into independent documents; held-out layouts combine and reorder some facts while preserving cross-document chains. Both use the same abstract corporate relation grammar. Both splits were authored/inspected during development; held-out scores are not a blind generalization estimate. Repeated abstract question patterns and a small controlled vocabulary limit diversity. No real-world quality claim is justified.

Runtime modules cannot import this file, the evaluation package, entity registry, or curated graph answers. Evaluation passes only question and k into the same service used by the API. Labels are used afterward to score the response.

## Metric definitions

Let D be a question's required document snapshots, F its required exact-span facts, R the returned chunks, and C its citations. Each fact is covered only when a returned chunk belongs to its exact document and fully contains the labeled quote at its labeled absolute offsets. A chunk that happens to mention the answer does not establish an intermediate step.

| Metric | Definition |
| --- | --- |
| Recall@k | Macro average of distinct required documents retrieved / size of D, on answerable questions |
| Precision@k | Macro average of returned chunks from D / number of chunks actually returned; zero for empty retrieval on an answerable question |
| Required-evidence coverage | Macro average of fully covered facts / size of F |
| Complete evidence-chain coverage | Fraction of answerable questions for which every fact in every required chain is covered |
| Answer exact-match | Casefolded, whitespace-normalized answer sets separated by semicolons equal the complete gold answer set; null matches only null |
| Answerable abstention | Fraction of answerable questions returning null |
| Correct unanswerable abstention | Fraction of unanswerable questions returning null |
| Citation correctness | Micro fraction of citations grounded in returned original text and matching a required fact's document, complete quote, and offsets |
| Unsupported answer count | Non-null responses with incorrect/incomplete expected answer, or without citations covering all required supporting facts |
| Query embedding latency | Wall time for queue wait and local question inference |
| Vector retrieval latency | Wall time for schema/build checks, index query, source validation, and response chunk construction |
| End-to-end service latency | Wall time from validated service request through generation; excludes client/network/HTTP serialization |

Retrieval metrics are undefined for unanswerable questions and represented as null, never a manufactured perfect score. Exact-match is also reported separately for hops 0/1/2/3. Citation correctness with zero citations is null, not 100%. Empty evidence chains do not count as complete. Unsupported count is a strict dataset-complete support measure; an answer may have a valid partial chain yet fail the full-set criterion. This distinction is visible in raw query records.

All metrics are computed at k=1,3,5,10, separately by hop and split. The standard final summary uses k=5. JSON contains individual scores, returned IDs, missed fact IDs, generation reasons, and timings. CSV exposes parallel per-query metric rows. Error analysis names failures at k=5 so retrieval failures can be separated from grammar/generation failures.

## Reproduction and performance scope

```powershell
uv run python -m scripts.build_baseline_dataset  # optional reproducible authoring
uv run python -m scripts.vector index
uv run python -m scripts.evaluate_baseline
```

The evaluation uses actual local MiniLM and actual Neo4j vector queries. Model warm-up is explicit, and cold worker startup plus first inference is measured separately. Here cold means a fresh inference process using already downloaded weights; the operating-system file cache is not forcibly cleared, and download time is excluded. Reported p50/p95 use linear interpolation over ordered samples. Main measurements use sequential requests (concurrency 1), two CPU inference threads, fixed corpus/configuration and k. Tests additionally exercise concurrent requests. Hardware/OS, RAM, process memory, package versions, Neo4j version, chunk count, and corpus build are recorded. Local timings are subject to Windows scheduling, cache state, and other applications; they are not production capacity estimates.

Required output: `reports/stage3/baseline_metrics.json`, `baseline_metrics.csv`, and `error_analysis.md`. See the Stage 3 report for actual measured results. No GraphRAG comparison or improvement claim is possible until a later stage implements and measures graph retrieval under the same conditions.

The benchmark extension introduces names outside Stage 2's reviewed entity registry. Its text is ingested and eligible for vector search even when graph extraction rejects those unfamiliar identities. A future graph comparison must first measure extraction coverage on this same frozen corpus; it cannot assume the benchmark's gold chains already exist as accepted graph edges or load gold answers into runtime. This is a material limitation for the next experiment, not evidence that graph retrieval will improve these scores.
