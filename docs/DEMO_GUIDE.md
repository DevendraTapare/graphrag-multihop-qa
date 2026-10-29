# Real Neo4j offline demo

Run these commands **inside the clean publication directory**, using Python 3.12, uv and Docker Desktop/Compose. The publication uses separate loopback ports 37477 (HTTP) and 37690 (Bolt), its own Compose project and its own volume. Do not substitute a research or shared database. The CLI requires a publication marker and a development database on loopback before it writes anything, and rejects the known research Bolt ports 7687, 17688 and 27689.

```powershell
uv sync --locked
uv run python -m scripts.setup_env
docker compose up -d --wait --wait-timeout 180
uv run python -m scripts.vector prepare-model
uv run python -m scripts.portfolio prepare --dataset demo
uv run python -m scripts.portfolio demo --output .local/demo-results.json
```

`setup_env` generates a fresh local password without printing it. Do not copy the research `.env`. First dependency installation, Docker image pull and model preparation require internet access. Once cached, the demo uses real local Neo4j, cached CPU MiniLM and fictional text only. It calls the existing vector, graph and hybrid services directly; it does not replay saved answers and does not depend on a paid API. It is an offline runner, not an HTTP load test. Source preparation reads fixture documents, discovers a registry, extracts facts, ingests current source runs, publishes a vector index and verifies every accepted fact's evidence. Repeat indexing must return the same cached build.

Eight cases are executed in all three modes, producing 24 actual responses:

| Case | Question | Expected graph/hybrid behavior |
|---|---|---|
| One hop | Which project does Priya (Lumen employee 001) manage? | Atlas |
| Two hops | Which database does the project managed by Priya (Lumen employee 001) use? | PostgreSQL |
| Three hops | Which cloud platform hosts the database used by the project managed by Priya (Lumen employee 001)? | AWS, with an actual three-edge path |
| Vector example | Which database does Project Atlas use? | PostgreSQL; vector answer also checked |
| Unknown | Which organization employs Nia Unlisted? | Abstain |
| Ambiguous identity | Which project does Lee Chen manage? | Abstain rather than choose a homonym |
| Missing evidence | Which organization employs Ivo? | Abstain |
| Unsupported grammar | Identify the cloud behind Priya's project database. | Abstain despite a legitimate intended question |

The runner records every real vector response, including chain questions on which it may abstain. It does not force vector to match graph answers. Graph/hybrid chain answers and all modes' negative cases are asserted after retrieval, and the three-hop response must include `reasoning_paths` and `hop_count: 3`. Inspect the JSON's `responses`, `citations`, `reasoning_paths`, `vector_evidence` and `reason` fields. For the three-hop case the path must follow the qualified Priya identity → Atlas → the Atlas-specific PostgreSQL instance → AWS. Each factual edge must refer to its exact fictional source evidence. An abstention has no invented answer citations.

The portfolio source publication is separate from the historical API's fixture/Stage 5 corpus wiring. Use this CLI for the documented reproducible demo. Existing API behavior and security are exercised by the real integration suite. Starting the API alone does not automatically build or expose this new CLI corpus.

For a small functional evaluation reproduction, prepare a separate 27-document subset and score nine questions across three modes:

```powershell
uv run python -m scripts.portfolio prepare --dataset smoke
uv run python -m scripts.portfolio evaluate --dataset smoke --output .local/smoke-results.json
```

The nine cases use worlds 0, 10 and 20, with question IDs 0, 3 and 7 in each world: an answerable one-hop question, an answerable two-hop question and an unknown identity. The template-world positives deliberately have unsupported question forms. World 20 contributes three calibration cases; the other six are from the final sets. This is an explicitly selected smoke subset, not the 180-question final benchmark. Labels are opened by the evaluator after preparation; the runtime receives only question text. To rebuild and rescore the complete 211-document, 198-question challenge, use `--dataset challenge` for both commands and a new output filename. That includes 18 calibration questions; filter them before reporting the 180-question final score. Outputs cannot overwrite an existing measured result. Preparation may take several minutes and reuses source versions idempotently.

Verify the package with:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest --run-integration -q --junitxml=.local/test-results.xml
uv run python -m scripts.check_ci_results .local/test-results.xml
```

Real integration tests start disposable Neo4j containers and load the pinned model. Do not run concurrent load experiments during these tests on a small machine. A one-CPU Docker host previously needed over 17 minutes for the full suite with other research containers running. Connection and model startup failures must be reported, never converted into skips. Hosted CI uses a 45-minute job budget but has not actually run.

The tests also ingest their owned fictional fixtures into the configured local database. After running them, repeat the relevant `prepare` command before replaying a stored demo publication; source-version checks deliberately reject a publication superseded by a different test ingestion. The legacy Stage 5/6 Compose files are excluded from this package because their project names and volumes target the preserved research setup. The CLI demo and challenge reproduction use only the isolated publication Compose service.

To stop only the publication container, run `docker compose down`. This preserves its named volume; do not add `-v` unless you intentionally want to erase the demo database. `.env`, `.local`, model cache and virtual environments are excluded from publication. Keep Neo4j and API bindings on loopback; this package is for local demonstration, without authentication or production availability claims.
