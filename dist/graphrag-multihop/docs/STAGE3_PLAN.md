# Stage 3 implementation plan

The audit covered README, Stage 1–2 reports, schema/provenance/extraction notes, migrations, source/chunk contracts, ingestion publication, and both existing evaluation sets. Stage 1 curated snapshots must remain byte-for-byte equivalent. Stage 2 document IDs hash logical source and original UTF-8 content; chunk IDs also bind processing version and exact Unicode offsets. Only a ready source whose current and desired run agree is published. Historical and unfinished chunks are not current evidence.

1. Pin real local MiniLM inference and a model revision; validate normalized 384-element vectors and reject text exceeding the tokenizer's 256-token window rather than silently truncate. Load once per process, serialize CPU inference, and bound work/waits.
2. Add migration 004 using Neo4j 5.26 Community list-of-float vector properties. Put embeddings on separate identity-bound records referencing canonical chunks by metadata, preserving all Stage 1–2 node properties and labels. Validate ONLINE schema before indexing/search.
3. Read only published canonical chunks. Stage a complete versioned corpus build in batches, then publish it atomically. Recheck source publication, hashes, and offsets on every read. Retain incomplete/old builds but exclude them. Repeat unchanged indexing without duplicate records.
4. Implement vector-only ANN retrieval and a conservative text-only deterministic answerer, with explicit infrastructure errors and a bounded query API. No factual edges, registry, or evaluation labels in runtime imports.
5. Author at least 100 labeled synthetic questions with one-/two-/three-hop chains, disjoint scenario splits, negatives and distractors. Gold authoring stays separate from runtime. Measure retrieval evidence and generation separately at k=1,3,5,10.
6. Test real inference, Neo4j indexing, isolated-database edge independence, provenance, concurrency, failed writes, stale builds, outages/recovery, and all Stage 1–2 regressions. Record controlled local performance and publish limitations and reproducible PowerShell commands. Stop after Stage 3.

The initial model download needs internet; subsequent runtime inference uses cached weights only. No paid provider, deployment, Git commit/push, or unrelated data deletion is planned.
