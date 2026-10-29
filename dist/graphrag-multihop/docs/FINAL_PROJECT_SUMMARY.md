# Final project summary

Stage 7A prepared a **CONDITIONAL GO portfolio candidate**. The project builds source-backed typed graphs from fictional text, validates actual multi-hop Neo4j paths, compares real local vector retrieval with graph and hybrid modes, and exposes citations and safe abstention behavior. Deterministic answer generation uses no paid generative LLM.

Stage 7A verification: 429 tests passed: 300 unit and 129 real Neo4j integration; zero final failures, errors or skips. Full-suite wall time: 1389.92 seconds. The real source-only demo executed 24 requests; the separate selected evaluation smoke executed 27. A new Python environment and dedicated database were used with cached packages/model/image. All original research files and database snapshots are preserved and checked.

The aligned inspected Stage 5 result was graph/hybrid 96/96 positive correctness. The new Stage 6 controlled challenge gave 54/128 for graph/hybrid and 0/128 for the frozen vector answerer. Hybrid complete text-chain coverage was 86/128 without better final answers. These are internally controlled synthetic comparisons, not universal accuracy or externally administered generalization evidence.

A connection-pool-only correction reduced repeated local 50-user graph/hybrid errors from 56/100 and 17/100 to 0/100 each, while p95 remained 17.27/17.91 seconds. Original historical failures remain visible. Sustained HTTP capacity and production availability are unverified.

The package excludes credentials, private logs, database files, models and caches. Secret scans found no actual credentials after exact false-positive triage. Stage 7B then upgraded the release dependencies and hardened XML/evidence checks: 436 tests now pass, with zero current audit findings and 12 reviewed LOW Bandit warnings. Two upstream advisory-status caveats remain disclosed. Stage 7B.2 adds MIT for authorized original material with separate third-party terms; hosted CI remains unverified. Read [STAGE7B_PRECOMMIT_REPORT.md](STAGE7B_PRECOMMIT_REPORT.md) for the current local commit gate. No publishing or deployment occurred. Read [STAGE7B_SECURITY_REVIEW.md](STAGE7B_SECURITY_REVIEW.md) for current results.

Read [STAGE7A_RELEASE_REPORT.md](STAGE7A_RELEASE_REPORT.md), [FINAL_EVALUATION.md](FINAL_EVALUATION.md), [DEMO_GUIDE.md](DEMO_GUIDE.md), [SECURITY_REVIEW.md](SECURITY_REVIEW.md) and [PUBLICATION_MANIFEST.md](PUBLICATION_MANIFEST.md).
