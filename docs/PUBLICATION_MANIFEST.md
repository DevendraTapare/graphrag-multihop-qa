# Publication manifest

The clean directory is `dist/graphrag-multihop/` in the research workspace. The directory is a local portfolio publication candidate, not a published repository or deployment. No project license is selected.

Final package: **328 files, 24727545 bytes (23.58 MiB)**, including this document, inventory and checksum file. Directory metadata and separately installed dependencies/model/container data are not included in that byte total.

## Included content

Source packages under `app`, four Cypher migrations, all required fictional source/evaluation datasets, all 423 historical test cases plus six new publication cases, source-only portfolio demo/evaluation CLI, primary historical comparison/error reports, new load/demo/smoke/security summaries, locked dependencies, Docker configuration and CI workflow. Historical stage documentation remains available; its time-specific statements are research history, not current readiness claims. Some historical JSON reports retain a UTF-8 byte-order mark to preserve their original hashes; use a BOM-aware reader such as Python `json.loads(path.read_bytes())`. The exact paths are listed in the publication checks.

New professional documentation: `README.md`, `docs/ARCHITECTURE.md`, `docs/PORTFOLIO_ARCHITECTURE.md` (same current architecture), `GRAPH_CONSTRUCTION.md`, `RETRIEVAL_MODES.md`, `ENGINEERING_DECISIONS.md`, `FINAL_EVALUATION.md`, `DEMO_GUIDE.md`, `SECURITY_REVIEW.md`, `THIRD_PARTY_NOTICES.md`, `RESUME_AND_INTERVIEW.md`, `STAGE7A_RELEASE_REPORT.md`, `FINAL_PROJECT_SUMMARY.md` and this manifest. The history directory keeps portable-link copies of the earlier README and Stage 1 architecture.

`FILE_INVENTORY.json` lists each payload path, byte size and SHA-256. It excludes itself and `SHA256SUMS` to avoid circular hashing. `SHA256SUMS` covers **every other package file**, including `FILE_INVENTORY.json`, and excludes only itself. Verify it with `sha256sum -c SHA256SUMS` where that command is available, or compare file bytes with Python hashlib on Windows. These hashes detect accidental changes; they are not a signed authenticity guarantee.

## Research preservation and declared differences

All 324 original research files, 55,020,369 bytes, retain their original hashes. Original archives, raw runs, failed attempts, logs and database snapshots stay in the research directory. A separate pre-Stage 7A research archive was created before packaging. No original README, architecture, CI, source, dataset or benchmark report was edited. New Stage 7A scripts/docs/reports and the clean directory were added. Database volumes were preserved and the research containers were restored; the snapshot checks are retained in `reports/stage7a/research_preservation.json`.

All original `app`, `data` and `migrations` bytes are unchanged in the release. All 129 integration tests are unchanged. The new `scripts/portfolio.py` is an adapter over existing services; source preparation does not read labels. Six new unit cases exercise its write guards and publication core-source preservation. One historical unit hash guard has a narrow documented layout adaptation: only declared docs/report/config differences or excluded report artifacts can differ; core/data preservation remains checked.

`PUBLICATION.json` records each original SHA, release SHA and reason for an override, and each original SHA/reason for an omitted research artifact. Additional portable history copies have corrected relative links. Declared overrides:

| Path | Reason |
|---|---|
| `.env.example` | Fresh isolated ports and tested pool size 50; no actual password |
| `.github/workflows/ci.yml` | Add actual CLI demo and explicit evaluation smoke after the unchanged full integration suite; hosted execution unverified |
| `.gitignore` | Exclude local demo state, nested dist and private key artifacts |
| `README.md` | Current professional README; historical README retained as a portable-link copy |
| `compose.yaml` | Separate publication project/volume and loopback 37477/37690 ports |
| `docs/ARCHITECTURE.md` | Current architecture; original Stage 1 architecture retained in history |
| `docs/AUTOMATIC_EXTRACTION.md` | Remove workstation-specific absolute paths |
| `docs/STAGE1_REPORT.md` | Remove workstation-specific absolute paths |
| `docs/STAGE2_REPORT.md` | Remove workstation-specific absolute paths |
| `docs/STAGE3_REPORT.md` | Remove workstation-specific absolute paths |
| `docs/STAGE4_REPORT.md` | Remove workstation-specific absolute paths |
| `docs/VECTOR_INDEXING.md` | Remove workstation-specific absolute paths |
| `tests/unit/test_graph_rag.py` | One hash guard adapted only for declared docs/config/report layout; protected core/data unchanged |

The new `.gitattributes` disables automatic line-ending conversion so later Git add/checkout does not silently invalidate historical byte hashes. See the [Git attributes documentation](https://git-scm.com/docs/gitattributes). No Git operation was performed. The release pool setting is 50, while the preserved research environment/default is ten. Isolated loopback ports are 37477/37690 and the publication Compose project is `graphrag-portfolio`; existing research volumes are not mounted. The two legacy sidecar Compose files are excluded because their project names target research volumes; the optional historical Stage 5 API URI in the template points to unused isolated port 37692 instead of a research database. The CI addition runs the actual portfolio demo and selected evaluation smoke after the complete test suite. Hosted execution remains UNVERIFIED.

## Exclusions and reproduction limits

Excluded: `.env` and actual credentials, private logs/XML/process records, model weights/caches, `.venv`, Python/test/lint caches, Docker database files/volumes, duplicate run copies, archive backups and large graph snapshots. Thirty-five original research files were deliberately omitted from the package; their original copies remain preserved and `PUBLICATION.json` lists the exact paths/reasons. A legacy recorder may require those excluded artifacts and can overwrite its own reports, so use the portfolio CLI documented in `DEMO_GUIDE.md` for clean source-only preparation and smoke reproduction. Historical low-level scripts are retained for inspection, not advertised as a fresh portable research-workspace restore.

The clean environment used a fresh virtual environment and fresh Neo4j volume with existing cached packages/model/image. Fresh Linux/GitHub execution and a completely uncached machine are not verified. The final artifact/path/secret and local Markdown link checks are recorded in `reports/stage7a/publication_checks.json`. Exact checksums and inventory are validated after all publication files are written.

Remaining publication conditions: choose and approve a project/data license, review source rights and third-party notices, remediate or explicitly accept the open Transformers advisory findings, and obtain a real GitHub CI result. Publishing needs a separate owner instruction. No commit, remote, push, deployment or Stage 7B was performed. See [STAGE7A_RELEASE_REPORT.md](STAGE7A_RELEASE_REPORT.md).
