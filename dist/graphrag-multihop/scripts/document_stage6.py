"""Render measured Stage 6 documentation from retained local artifacts; no runtime tuning."""

# Report paragraphs/table rows are single literals, preserving Markdown paragraph boundaries.
# ruff: noqa: E501

import json

from defusedxml import ElementTree as ET

from app.graph.fixtures import ROOT
from scripts.stage6_support import OUT, access, read, save

NAMES = {"vector_only": "Vector", "graph_only": "Graph", "hybrid_graph_vector": "Hybrid"}


def pct(value):
    return "N/A" if value is None else f"{100 * value:.2f}%"


def ms(pair):
    return f"{pair['p50']:.2f} / {pair['p95']:.2f}"


def write(name, lines):
    (ROOT / "docs" / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    access(
        "read derived scored labels to generate final measured documents; no tuning",
        OUT / "challenge_results.json",
    )
    result = read("challenge_results.json")
    load = read("load_results.json")["results"]
    recovery = read("recovery_results.json")
    identity = read("identity_audit.json")
    pool = read("pool_diagnostic.json")
    cases = list(ET.parse(ROOT / "reports/stage6-tests.xml").getroot().iter("testcase"))
    if not (
        len(cases) >= 423
        and all(
            not any(c.find(k) is not None for k in ("failure", "error", "skipped")) for c in cases
        )
    ):
        raise AssertionError("Tests must finish and pass")
    unit = sum(".unit." in c.attrib["classname"] for c in cases)
    integration = sum(".integration." in c.attrib["classname"] for c in cases)
    rows = [r for r in result["queries"] if r["split"] != "calibration"]
    hop_table = [
        "| Mode | One hop (80) | Two hops (36) | Three hops (12) | Positive answers (128) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    evidence_table = [
        "| Mode | Required evidence recall | Full textual chain | Validated graph chain | False abstentions | Correct unanswerable abstentions |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    split_table = [
        "| Mode | Document-held-out positive accuracy | Template-held-out positive accuracy | Final overall accuracy including abstentions |",
        "| --- | ---: | ---: | ---: |",
    ]
    timing_table = [
        "| Mode | Document-held-out p50/p95 ms | Template-held-out p50/p95 ms | All final questions p50/p95 ms |",
        "| --- | ---: | ---: | ---: |",
    ]
    for mode, name in NAMES.items():
        scores = []
        for h in (1, 2, 3):
            selected = [r for r in rows if r["mode"] == mode and r["answerable"] and r["hops"] == h]
            n = sum(r["exact_match"] for r in selected)
            scores.append(f"{n}/{len(selected)} = {pct(n / len(selected))}")
        s = result["summary"][mode]
        f = s["final"]
        hop_table.append(
            f"| {name} | " + " | ".join(scores) + f" | {pct(f['answerable_accuracy'])} |"
        )
        evidence_table.append(
            f"| {name} | {pct(f['required_evidence_recall'])} | {pct(f['complete_chain_coverage'])} | {pct(f['validated_graph_chain_coverage'])} | {f['false_abstentions']}/128 | 52/52 |"
        )
        split_table.append(
            f"| {name} | {pct(s['document_held_out']['overall']['answerable_accuracy'])} | {pct(s['template_held_out']['overall']['answerable_accuracy'])} | {pct(f['answer_exact_match'])} |"
        )
        timing_table.append(
            f"| {name} | {ms(s['document_held_out']['overall']['latency_ms'])} | {ms(s['template_held_out']['overall']['latency_ms'])} | {ms(f['latency_ms'])} |"
        )
    load_table = [
        "| Mode | Users | Requests | Answers | Correct abstentions | False abstentions | Errors | Explicit request-budget timeouts | p50/p95 ms | Completed requests/s | Correct results/s |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    category_table = [
        "| Final category | Questions | Answerable | Vector exact match | Graph exact match | Hybrid exact match |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for tag in (
        "unanswerable",
        "ambiguous",
        "conflicting",
        "paraphrased",
        "multiple_answers",
        "missing_evidence",
    ):
        selected = {
            m: [
                r
                for r in rows
                if r["mode"] == m
                and (not r["answerable"] if tag == "unanswerable" else tag in r["tags"])
            ]
            for m in NAMES
        }
        group = selected["graph_only"]
        scores = [pct(sum(r["exact_match"] for r in selected[m]) / len(selected[m])) for m in NAMES]
        category_table.append(
            f"| {tag} | {len(group)} | {sum(r['answerable'] for r in group)} | "
            + " | ".join(scores)
            + " |"
        )
    for r in load:
        c = r["outcomes"]
        good = c.get("successful_answer", 0) + c.get("correct_abstention", 0)
        load_table.append(
            f"| {NAMES[r['mode']]} | {r['users']} | {r['total_requests']} | {c.get('successful_answer', 0)} | {c.get('correct_abstention', 0)} | {c.get('false_abstention', 0)} | {c.get('error', 0)} | {c.get('timeout', 0)} | {ms(r['latency_ms'])} | {r['throughput_requests_per_second']:.2f} | {good / r['duration_seconds']:.2f} |"
        )
    report = [
        "# Stage 6 report",
        "",
        "Verdict: **CONDITIONAL**. The evaluation and reliability work is complete, but language generalization and high-concurrency reliability remain weak. This is a NEW CONTROLLED CHALLENGE SET, not an independent external benchmark.",
        "",
        "## What changed",
        "",
        "Only README.md and docs/PROJECT_ROADMAP.md changed among the 241 existing files. New files provide the isolated challenge, source-only builder/runtime adapter, frozen evaluator, load/PROFILE/recovery tools, CI workflow, tests, six Stage 6 documents and retained reports. The complete hashed list is in reports/stage6/FILE_MANIFEST.md. No app implementation, historical fixture, migration, dependency lock or Stage 1–5 metric file changed. Both historical databases remain unchanged.",
        "",
        "## Verification",
        "",
        f"**{len(cases)} tests passed: {unit} unit and {integration} real Neo4j integration. Zero failures, errors or skips. All 412 previous tests remain present and pass.** This includes migration, extraction, provenance, filesystem, vector, graph, hybrid and adversarial checks. Ruff lint/format and the locked dependency check pass. The actual HTTP startup/outage/recovery exercise passes. Hosted GitHub CI is **UNVERIFIED**; workflow syntax and its commands were validated locally on Windows, not on a hosted Ubuntu runner.",
        "",
        "The first full regression attempt passed 422 tests and failed one existing homonym test during fixture ingestion: a three-second connection-pool acquisition timeout occurred before its identity assertions. The failed XML and log are preserved, and regression_attempts.json records both attempts. The complete rerun used the same runtime, limits and assertions, with the unused Stage 6 container stopped to reduce resource pressure. The final counts above describe that complete passing rerun; the earlier failure is not discarded.",
        "",
        "## Data and independence",
        "",
        "There are **180 final questions**: 90 document-held-out and 90 template-held-out. Another 18 questions form a separate calibration set, giving 198 total questions. Final sets each have 64 positives and 26 unanswerable questions. They use 20 newly authored fictional worlds; two additional worlds are calibration. The combined isolated corpus contains **211 documents/chunks, 260 new stored canonical identities and 243 accepted source facts**. The source-derived registry has 287 entries, including 27 inherited reviewed identities that are not stored in this challenge graph. No standalone curated facts were loaded.",
        "",
        "All 243 accepted facts passed independent source-provenance validation. Ingestion and indexing were repeated without duplicate publications. There were 48 sentence rejections: 44 non-asserted statements and four unsupported patterns. Other unfamiliar usage/hosting structures produced no relationship candidates. Thirty-four documents have no accepted facts. The builder reads sources only; it does not import gold IDs, expected answers or paths. Runtime files and configuration were frozen before final labels were materialized. Both scoring runs preserve every failure and match **594** non-timing mode/question comparisons (198 questions × three modes).",
        "",
        f"The identity audit records {identity['repeated_mentions_coalesced']} repeated exact source mentions mapped to existing canonical entries. These are source-policy coalescences, not externally verified identity merges. There are zero inherited historical identities stored and zero duplicate canonical IDs; explicit employee-qualified homonyms remain distinct. Full source-span-to-registry candidate mappings are retained in identity_audit.json.",
        "",
        "The author knew the scenario and template design. The local seal/access log is process discipline, not external custody. Document holdout tests new source identities with related grammar combinations; template holdout tests new productions. Repeated synthetic worlds are correlated. See STAGE6_EVALUATION_PROTOCOL.md and STAGE6_GENERALIZATION.md for the full Stage 5 exposure audit and limits.",
        "",
        "## Quality",
        "",
        "Historical Stage 5 used 92 source documents and the previously inspected 122-question benchmark:",
        "",
        "| Historical mode | One hop | Two hops | Three hops | Full textual chain |",
        "| --- | ---: | ---: | ---: | ---: |",
        "| Vector | 97.22% | 25.00% | 4.17% | 46.88% |",
        "| Graph | 100% | 100% | 100% | 100% |",
        "| Hybrid | 100% | 100% | 100% | 100% |",
        "",
        "The new challenge below is a different question/source distribution, not a before/after optimization. Document holdout also changes question forms from Stage 5; it does not isolate document novelty alone. In particular, vector's zero end-to-end accuracy is an answerer grammar finding, not proof that vector retrieval failed to find useful text.",
        "",
        *hop_table,
        "",
        *split_table,
        "",
        *evidence_table,
        "",
        *category_table,
        "",
        "Category groups overlap and exact-match rates include correct abstentions. They must not be summed or called successful positive reasoning. In particular, template-held-out conflict/ambiguity cases reject grammar before testing contradictions or identity resolution.",
        "",
        "Graph and hybrid return 54/128 positive answers. Their complete graph-proof coverage is 54/128. Graph has 88/88 correct citations; hybrid has 88/88. Vector has no answer citations, so citation correctness is N/A. All modes have **zero unsupported final answers, zero incorrect citations and zero source-invalid citations** at top_k=5 on this challenge. All correctly abstain on 52 unanswerable questions. This does not prove contradiction recognition when a question is rejected before interpretation. The historical vector k=1 partial-set failure is preserved.",
        "",
        "Wrong-entity resolutions: graph 0/50 checked question starts, hybrid 0/50; vector exposes no canonical linker, so N/A. These are scoped checks, not a universal entity-resolution guarantee. Ambiguous names remain unresolved. Source construction contains all required accepted facts for 108/128 positives (84.38%). Missing extraction affects 20 positives across both final sets. Graph/hybrid primary failures are ten extraction failures in document holdout plus 64 unsupported query forms in template holdout; ten of those template questions also have extraction gaps. Vector's 128 false abstentions are attributed to its unsupported answerer grammar, even though retrieved text contains complete evidence for 58 questions.",
        "",
        "Hybrid has zero uniquely correct positive answers, graph has zero uniquely correct positives versus hybrid, and vector has zero uniquely correct positives. Graph and hybrid jointly answer 54 positives that vector does not. Hybrid introduces no additional wrong answers here. It improves textual chain coverage through extra chunks but cannot turn unsupported question syntax or missing graph facts into final answers under its declared proof policy. Reranking/candidate discovery is not a general semantic question interpreter. For supported structured questions with extracted source evidence, graph-only remains the simpler measured choice. No universal mode preference is established.",
        "",
        "## Warm performance",
        "",
        *timing_table,
        "",
        "The combined graph median is dominated by immediate unsupported-template abstentions. It is not an answered-query speed improvement. Document-held-out timings are more useful for the supported workload. Cold local model first encode took "
        + f"{read('challenge_run2.json')['configuration']['cold_model_first_encode_ms'] / 1000:.2f} seconds in the second scoring run; cached weights, no OS cache flush. Per-request phases and both runs remain in JSON. Sources, upfront discovery and final evidence budgets are not equalized across modes: top_k=5 limits vector candidates, not the graph's final evidence count.",
        "",
        "## Fifty-user results",
        "",
        *load_table[:2],
        *[line for line, r in zip(load_table[2:], load, strict=True) if r["users"] == 50],
        "",
        "These are short service-level bursts (100 requests/mode), not sustained HTTP or production capacity. Completed throughput includes errors and false abstentions. Correct-results throughput counts correct answers and correct abstentions. Pool-acquisition and driver read timeouts are included in database errors, not the explicit application-budget timeout column. A separate 50-request diagnostic observed 28 ConnectionAcquisitionTimeoutError causes. Host CPU reached 100%. Pool occupancy is N/A; configured maximum is ten. See STAGE6_PERFORMANCE.md for every level, query plans and embedding contention.",
        "",
        "Hybrid had fewer database errors than graph in the 50-thread burst (14 versus 49), but its 100 requests took 36.28s rather than 9.00s. It delivered 2.37 correct results/s versus graph's 5.67. Its serialized embedding stage may stagger database demand; this is an inference, not a measured admission-control mechanism. This reliability difference does not create a uniquely correct challenge answer or establish better production capacity.",
        "",
        "## Recovery",
        "",
        f"Neo4j became Bolt-ready **{recovery['startup_to_bolt_ready_ms'] / 1000:.2f} seconds** after the start command. After readiness, the first graph query with a loaded model took **{recovery['warm_model_first_after_recovery']['graph_only']['wall_ms'] / 1000:.2f} seconds**. The subsequent vector and hybrid queries took {recovery['warm_model_first_after_recovery']['vector_only']['wall_ms'] / 1000:.2f} and {recovery['warm_model_first_after_recovery']['hybrid_graph_vector']['wall_ms'] / 1000:.2f} seconds. A fresh API/model hybrid query took **{recovery['http_fresh_model_first_after_recovery']['wall_ms'] / 1000:.2f} seconds**, including {recovery['http_fresh_model_first_after_recovery']['response']['body']['latency_ms']['embedding_generation'] / 1000:.2f} seconds in model startup/embedding. These are sequential measurements, not exchangeable cold conditions.",
        "",
        "The interrupted request failed safely. Database-unavailable queries returned 503 in all modes; liveness stayed 200 and readiness recovered to 200. Subsequent HTTP hybrid calls took "
        + ", ".join(f"{r['wall_ms'] / 1000:.2f}s" for r in recovery["http_subsequent_warm"])
        + ". Recovery remains variable; the earlier 20.02-second query cannot be attributed only to embedding or only to database startup. See STAGE6_RELIABILITY.md.",
        "",
        "## Remaining limits",
        "",
        "Finite extraction and question grammars, synthetic correlated cases, controlled identity assumptions, a 211-document corpus, strict global publication availability, different evidence budgets, pool pressure, embedding serialization and cold database/model behavior remain material limits. No final challenge tuning or performance optimization was made. No paid provider, remote repository, commit, push or deployment was used. **Work stops after Stage 6. Stage 7 is not started.**",
    ]
    write("STAGE6_REPORT.md", report)
    performance = [
        "# Stage 6 performance",
        "",
        "This measures the unchanged frozen runtime. It does not establish production scalability.",
        "",
        "## Sequential evaluation",
        "",
        *timing_table,
        "",
        "The all-final graph median mostly measures unsupported-template rejection without a database read. Compare the document-held-out distribution and actual supported PROFILE probes for traversal costs. Model startup is excluded from warm quantiles. Inputs and configuration hashes, Python/Neo4j/model versions, hardware and both full scored runs are retained. The machine reports one physical/logical CPU and approximately 14.9 GB RAM. Three persistent local Neo4j instances were running; historical instances received no benchmark traffic. No load, outage or regression tests overlapped scoring. No OS cache flush was performed.",
        "",
        "## Bounded load",
        "",
        "Two closed-loop waves per user count, one request per thread per wave; separately per mode. Calibration probes span one-/two-/three-hop chains and one absent-entity query. The smallest levels do not have identical probe proportions to the larger levels. Primary total: 546 requests across all fifteen mode/level combinations. Full raw outcomes, database call wall times, embedding lock-inclusive times and resource samples are in load_results.json.",
        "",
        *load_table,
        "",
        "Completed throughput counts failures as completed requests. Correct-results throughput includes correct answers and correct abstentions, not false abstentions or errors. No result should be called a capacity guarantee. Explicit request-budget timeout categories were zero; database errors include acquisition/read timeouts. One driver socket read timeout is retained in the primary log; supplementary cause instrumentation found 28 pool-acquisition timeouts in 50 graph requests, with limits and queries unchanged. The supplementary numbers are not substituted for the primary failures.",
        "",
        "At 50 users, database call wall p50/p95 and embedding contention were:",
        "",
        "| Mode | Database call wall p50/p95 ms | Embedding lock-inclusive p50/p95 ms |",
        "| --- | ---: | ---: |",
    ]
    for r in load:
        if r["users"] == 50:
            performance.append(
                f"| {NAMES[r['mode']]} | {ms(r['database_call_wall_ms'])} | {ms(r['embedding_lock_inclusive_ms'])} |"
            )
    performance += [
        "",
        "Database wall time includes pool acquisition, network and server work. It is not server CPU time. In the supplementary diagnostic, Neo4j summary available-after p50/p95 was "
        + ms(pool["server_available_after_ms"])
        + " ms and consumed-after was "
        + ms(pool["server_consumed_after_ms"])
        + " ms. Those driver summary fields exclude connection-pool wait and are not pure execution CPU. Internal pool occupancy is unavailable through the supported public API; configured size is ten. The single local embedding worker serializes inference. Lock-inclusive timings include both waiting and inference, not a separately measured wait counter.",
        "",
        "Host CPU reached 100%. JSON samples record host used memory and runner RSS; they do not isolate model-worker or database-container RSS. Short bursts, OS scheduling and the shared Docker/Windows host limit comparisons.",
        "",
        "## Actual query plans",
        "",
        "PROFILE was executed on actual calibration paths and source/provenance reads with trusted parameters. One-/two-/three-hop graph requests made 16/18/20 round trips. Unique PROFILE query sets contain NodeUniqueIndexSeek for entity/source/run/document lookups and DirectedRelationshipUniqueIndexSeek for sealed assertion IDs. Path expansion is typed, explicitly one to three hops, and capped. There is no unbounded relationship expression or user-authored Cypher.",
        "",
        "Capture and final revalidation repeat source-publication checks, path prefixes and batched metadata reads intentionally. Metadata is batched, rather than one query per individual fact, but repeated full-publication validation adds fixed work. The whole:Chunk ingestion lookup uses NodeByLabelScan: on the three-hop probe it produced 633 scan rows and 636 DB hits for 211 physical chunks. The source proof reconstructs approved source facts with a request-local cache. Exact profiles, parameters, DB hits and driver server summary timings remain in query_plans.json.",
        "",
        "Measured bottlenecks are many round trips, the metadata scan, full-publication checks, pool acquisition and serialized embeddings. No safety/provenance check was removed, no pool/retry limit was silently widened and no index/runtime optimization was made after freezing. A future calibration-only experiment could measure a chunk ingestion index or fewer round trips while preserving snapshot/provenance semantics; that work is not started here.",
    ]
    write("STAGE6_PERFORMANCE.md", performance)
    reliability = [
        "# Stage 6 reliability and recovery",
        "",
        "The real exercise used only compose.stage6.yml, project graphrag-stage6, ports 27476/27689 and its own persistent volume. The historical containers and volumes stayed running. All captured request/result phases are in recovery_results.json; recovery_attempt.json preserves partial/final state as well.",
        "",
        "## Measured sequence",
        "",
        f"API startup to liveness: {recovery['api_startup_ms'] / 1000:.2f}s. Initial fresh API/model hybrid query: {recovery['http_cold_first']['wall_ms'] / 1000:.2f}s. A separate in-process model was then loaded before the outage. The database was stopped after the first actual path read of an in-flight request, before remaining source proof/revalidation. This tests interruption between real read phases, not interruption in the middle of a single server operator. That request failed safely after {recovery['interrupted_request']['wall_ms'] / 1000:.2f}s; the time includes the coordinated stop. It returned no partial answer.",
        "",
        "During outage, all three HTTP modes returned safe 503 bodies with request IDs and no answer/path. Liveness remained 200; aligned readiness was 503. The API was restarted while Neo4j was down and remained live/unready. No fallback answer was generated.",
        "",
        "| Measurement | Time |",
        "| --- | ---: |",
        f"| Start command through Bolt readiness | {recovery['startup_to_bolt_ready_ms'] / 1000:.2f}s |",
        f"| Vector-index readiness check after Bolt | {recovery['index_readiness']['wall_ms'] / 1000:.2f}s |",
        f"| First graph query after readiness, model already loaded | {recovery['warm_model_first_after_recovery']['graph_only']['wall_ms'] / 1000:.2f}s |",
        f"| Next vector query, same loaded model | {recovery['warm_model_first_after_recovery']['vector_only']['wall_ms'] / 1000:.2f}s |",
        f"| Next hybrid query, same loaded model | {recovery['warm_model_first_after_recovery']['hybrid_graph_vector']['wall_ms'] / 1000:.2f}s |",
        f"| Fresh driver connection/readiness after warming | {recovery['fresh_connection_readiness']['wall_ms']:.2f}ms |",
        f"| Fresh API/model hybrid query after recovery | {recovery['http_fresh_model_first_after_recovery']['wall_ms'] / 1000:.2f}s |",
        "",
        "Order matters: graph, then vector, then hybrid share database warm-up. The fresh connection probe is measured after database warm-up and cannot be used to subtract a first cold handshake. Bolt readiness does not guarantee warm query plans or caches. The first graph request spent 17.02s in capture/traversal including the global publication seal, 1.48s in provenance and 0.74s in revalidation. Pure path CPU, disk I/O, plan compilation and JVM/OS warm-up were not separately measured within that capture phase. Actual PROFILE plans provide a separate warm-query view.",
        "",
        "The fresh API/model recovered request spent 15.77s in model startup/embedding, 0.82s in vector search, 0.84s in graph capture, 0.05s in provenance and 0.54s in revalidation. Its HTTP wall total was 18.23s. Subsequent hybrid HTTP wall times were "
        + ", ".join(f"{r['wall_ms'] / 1000:.2f}s" for r in recovery["http_subsequent_warm"])
        + ". These remain variable and are not all subsecond.",
        "",
        "## Why Stage 5's 20.02 seconds needs caution",
        "",
        "Both cold model startup and cold database query work can be substantial. The Stage 5 timing was one first recovered request without this full decomposition. Stage 6 does not prove its exact cause retrospectively. The new measurements show a loaded-model graph request near twenty seconds and a fresh-model hybrid request near eighteen seconds. Database process startup is another 53.78-second interval before either query measurement.",
        "",
        "## Bounds and safety",
        "",
        "Read driver managed retry time remains zero. Application reads use auto-commit session.run, not a hidden managed retry loop. Ingestion alone uses managed writes with a three-second retry maximum. Connection/acquisition timeout remains three seconds, pool maximum ten, graph query maximum ten seconds bounded by remaining budget, graph request target twenty seconds and hybrid target sixty seconds. Neo4j Query transaction timeouts and remaining-budget checks remain intact. [Official query manual](https://neo4j.com/docs/python-manual/current/query-simple/) and [driver configuration/API](https://neo4j.com/docs/api/python-driver/current/api.html) describe these distinct controls.",
        "",
        "Budgets are checked between bounded operations; this is not a hard OS cancellation deadline. Load errors show that deadlines do not guarantee successful recovery/capacity. Index readiness is checked separately from database connectivity. The readiness endpoint checks connectivity only, not model warmth, full source publication or answerability. Final provenance revalidation is not atomic through HTTP delivery. No safety check was disabled to improve latency.",
    ]
    write("STAGE6_RELIABILITY.md", reliability)
    general_path = ROOT / "docs/STAGE6_GENERALIZATION.md"
    original = general_path.read_text(encoding="utf-8").split(
        "\n## Final measured challenge results\n"
    )[0]
    general_path.write_text(
        original
        + "\n\n## Final measured challenge results\n\n"
        + "\n".join(split_table + [""] + hop_table + [""] + evidence_table)
        + "\n\nThe document-held-out set loses ten positive answers through extraction gaps. The template-held-out set loses all 64 positives through unsupported interpretation. Unfamiliar statements include responsibility resting with a person, a project relying on a database, and a platform providing hosting. None is added manually to the graph. Twelve source-level semantic statements across four final worlds are unextracted; these affect twenty final positive questions. Source construction fully covers 108/128 positives, while the query interpreter still blocks template-held-out questions.\n\nVector retrieves complete text evidence for 58/128 positives but its answerer rejects every new question form. Hybrid text covers 86/128 complete chains, yet it produces the same 54 positive answers as graph-only. This demonstrates why evidence coverage, answerer coverage and final accuracy must be separate. A safe grammar rejection is a false abstention on an answerable question.\n\nAll four final contradiction questions receive abstentions. Only the two document-held-out cases actually reach conflicting graph facts; template-held-out cases reject syntax first. The twenty final bare-homonym questions also abstain; unsupported grammar explains the template half. These should not be counted as twenty successful disambiguations or four successful contradiction detections. Graph and hybrid resolve zero wrong entities in fifty checked explicit starts; vector has no canonical resolution metric. Similar-name identity checks also pass in real integration tests.\n\nThe primary failure inventory preserves every failed/abstained row and runtime reason. No before/after quality improvement is claimed because runtime/configuration was not tuned. Hybrid-only, graph-only-exclusive and vector-only-exclusive positive wins are all zero; graph/hybrid jointly outperform vector on 54 positives. New sentence interpretation or semantic candidate linking would need new calibration work and another sealed evaluation, not final-question patches.\n",
        encoding="utf-8",
    )
    security = ROOT / "docs/STAGE6_SECURITY.md"
    original = security.read_text(encoding="utf-8").split("\n## Final verification\n")[0]
    security.write_text(
        original
        + f"\n\n## Final verification\n\n{len(cases)} checks passed: {unit} unit and {integration} real Neo4j integration, no skips/errors/failures. All 412 earlier tests are preserved. All 243 challenge facts passed provenance validation. Final evaluation: zero unsupported answers, zero incorrect citations and zero invalid source spans. Graph/hybrid citations are 88/88 correct; vector citation correctness is N/A because it abstains on every final positive. The bounded load errors and real outage failures remain reported; they are not silently scored as safe successful answers.\n",
        encoding="utf-8",
    )
    # Retain the observed setup failure and driver stderr alongside successful final runs.
    driver_lines = [
        line
        for line in (ROOT / ".pytest_cache/stage6-load.log")
        .read_text(encoding="utf-8")
        .splitlines()
        if "<CONNECTION>" in line or "SocketDeadline" in line
    ]
    save(
        "environment_attempts.json",
        {
            "setup_attempt_1": {
                "result": "DatabaseUnavailable during first migration before Bolt warmed",
                "cause": "ServiceUnavailable: four-byte Bolt handshake exceeded three-second connection deadline",
                "scored": False,
            },
            "setup_attempt_2": {
                "result": "Source-only build/provenance/index validation succeeded",
                "added_before_freeze": "Bounded readiness probes before migration",
            },
            "load_driver_diagnostics": driver_lines,
            "note": "All scored runs are retained separately; no failed scored run was replaced",
        },
    )
    print(json.dumps({"documents_written": 6, "tests": len(cases), "verdict": "CONDITIONAL"}))


if __name__ == "__main__":
    main()
