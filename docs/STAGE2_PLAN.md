# Stage 2 implementation plan

Audit: Stage 1 has seven domain labels, five factual edge types, three structural edge types, immutable fixture payloads, two checksum-tracked migrations, and 78 tests. Automatic facts can share canonical entity IDs, but must not change curated properties or reuse curated assertion IDs. The fixture validator must distinguish ingestion-owned assertions from unexpected unowned edges. Migration regression expectations must include the new migration explicitly.

1. Load only bounded local fictional TXT/Markdown files or the existing fixture texts. Keep immutable content snapshots, original Unicode text, hashes, and deterministic chunk offsets.
2. Extract controlled aliases and approved sentence patterns. Resolve against a versioned registry; ambiguous people and deployment names require explicit trusted context or rejection.
3. Recheck source/hash/version, exact spans, grounded mentions, approved patterns, directions, and canonical IDs before writing. Keep automatic provenance separate from manual provenance.
4. Add a managed-transaction writer with deterministic assertion IDs, small batches, per-source claim tokens/leases, and an atomic ready publication step. Read automatic assertions only through a current-source/ready-run gate. Keep old source versions as hidden history and preserve other sources.
5. Provide a local CLI for ingestion, status, rejections, conflicts, and provenance inspection. Add no HTTP mutation endpoint.
6. Author separate calibration/held-out extraction labels, measure quality, test failures/concurrency/retries against Neo4j, rerun Stage 1 checks, and document measured results and limitations.
