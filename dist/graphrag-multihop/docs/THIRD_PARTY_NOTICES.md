# Current license notice

Stage 7B.2 adds the owner-approved MIT license for authorized first-party material, Copyright (c) 2026 Devendra Tapare. Third-party terms remain separate. The current inventory is [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). The dated review below is preserved as historical context.

# Third-party and licensing review

No project license was selected or added during Stage 7A. The owner must decide how to license the original code and fictional datasets before public publication and confirm rights to distribute them. This document records dependency information; it does not grant a license for the project or resolve legal compatibility questions.

The release distributes source, data and lock/configuration files, not Neo4j binaries, model weights or installed Python packages. `uv.lock` records exact resolved packages and hashes; `reports/stage7a/dependency_metadata.json` records the installed distributions' own declared license metadata where available. Metadata is not a substitute for inspecting upstream license and notice files when redistributing dependencies.

| Component | Observed upstream declaration | Scope |
|---|---|---|
| Neo4j Community | GPL v3 | Downloaded separately as a pinned container; see [Neo4j legal terms](https://neo4j.com/legal-terms/) and [source repository](https://github.com/neo4j/neo4j) |
| Neo4j Python driver 6.4.1 | Apache-2.0 AND Python-2.0 in installed metadata | Installed by uv; not vendored |
| all-MiniLM-L6-v2 | Apache 2.0 in the [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/README.md) | Exact pinned revision is downloaded separately; no weights bundled |
| sentence-transformers 5.7.0 | Apache-2.0 in installed metadata | Python dependency |
| FastAPI 0.162.0 | MIT in installed metadata | Python dependency |
| PyTorch 2.14.1 | Multiple Apache/BSD/MIT/LLVM/BSL expressions in installed metadata | Review full upstream notices before binary redistribution |

All evaluation worlds and documents in this release are controlled fictional fixtures, not scraped proprietary or personal datasets. Technology and cloud names are labels in those fictional examples; no external customer records or private source documents are included. Historical reports describe the fixture authorship and construction process. Synthetic source authorship still needs the owner's rights review before public licensing.

Package checks exclude `.env`, local credential files, private logs, Docker volumes, model caches and virtual environments. Tool executables downloaded for scans remain in the private research cache and are not bundled. Review the final manifest and [SECURITY_REVIEW.md](SECURITY_REVIEW.md) together with this document before choosing a publication license. No external publication action is authorized or performed by this report.

Stage 7B updates the release dependency lock without selecting a project license. Current installed dependency metadata is in [dependency-metadata.json](../reports/stage7b/dependency-metadata.json), and every lock change is in [dependency-changes.json](../reports/stage7b/dependency-changes.json). The earlier Stage 7A metadata remains a dated record. No dependency binary is bundled.
