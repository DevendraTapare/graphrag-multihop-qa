"""Create final public reports only from completed verification evidence."""

# ruff: noqa: E501

import json
import shutil
import xml.etree.ElementTree as ET

from scripts.stage7a_support import OUT, RELEASE, ROOT, check_research, digest, read, save


def write_doc(name, text):
    (ROOT / "docs" / name).write_text(text.strip() + "\n", encoding="utf-8")
    shutil.copyfile(ROOT / "docs" / name, RELEASE / "docs" / name)


def test_summary():
    cases = list(ET.parse(OUT / "release-tests.xml").getroot().iter("testcase"))
    issues = [
        {"name": c.attrib["name"], "class": c.attrib["classname"], "issue": kind}
        for c in cases
        for kind in ("failure", "error", "skipped")
        if c.find(kind) is not None
    ]
    return {
        "tests": len(cases),
        "unit": sum("unit" in c.attrib["classname"] for c in cases),
        "integration": sum("integration" in c.attrib["classname"] for c in cases),
        "failures_errors_skips": issues,
        "passed": len(cases) - len(issues),
        "original_cases_retained": 423,
        "new_publication_cases": 6,
        "historical_guard_adaptations": 1,
        "integration_test_changes": 0,
    }


def main():
    preservation = check_research()
    validation, tests = read("validation_resolved.json"), test_summary()
    if tests["failures_errors_skips"]:
        raise ValueError("Resolve or report verification failures before finalizing")
    assert (tests["tests"], tests["unit"], tests["integration"]) == (429, 300, 129)
    if any(s["exit_code"] for s in validation["steps"]):
        raise ValueError("Verification contains failed steps")
    demo, smoke = read("fresh-release-demo.json"), read("release-smoke.json")
    assert demo["requests"] == 24 and smoke["requests"] == 27
    assert demo["provenance"]["failures"] == 0
    tests["final_unit_recheck"] = read("final_unit_recheck.json")
    save("release_test_results.json", tests)
    summary = {
        "demo": {
            "requests": demo["requests"],
            "cases": demo["cases"],
            "source_only_build": demo["source_only_build"],
            "provenance": demo["provenance"],
        },
        "smoke": {
            "questions": smoke["questions"],
            "requests": smoke["requests"],
            "positive_questions_per_mode": 6,
            "negative_questions_per_mode": 3,
            "modes": {},
        },
    }
    for mode in ("vector_only", "graph_only", "hybrid_graph_vector"):
        rows = [r for r in smoke["rows"] if r["mode"] == mode]
        summary["smoke"]["modes"][mode] = {
            "rows": len(rows),
            "metric_keys": sorted(set(rows[0]) - {"response"}),
            "answers": [r["response"]["answer"] for r in rows],
            "abstentions": sum(r["response"]["abstained"] for r in rows),
            "unsupported_answers": sum(r["unsupported_answer"] for r in rows),
        }
    save("demo_smoke_summary.json", summary)
    # Keep raw private logs, absolute paths, XML and verbose advisory descriptions outside.
    public = (
        "load_pool10_repeat.json",
        "load_pool50_repeat.json",
        "load_comparison.json",
        "release_test_results.json",
        "fresh-release-demo.json",
        "fresh_demo_verification.json",
        "release-smoke.json",
        "demo_smoke_summary.json",
        "dependency_metadata.json",
        "dependency_audit_summary.json",
        "static_analysis_summary.json",
        "gitleaks_triage.json",
        "repository_audit_summary.json",
        "environment_comparison.json",
        "final_unit_recheck.json",
        "smoke_build_verification.json",
        "research_preservation.json",
    )
    target = RELEASE / "reports/stage7a"
    target.mkdir(parents=True, exist_ok=True)
    for name in public:
        shutil.copyfile(OUT / name, target / name)
    table = []
    for row in read("load_comparison.json")["rows"]:
        if row["users"] == 50:
            table.append(
                f"| {row['pool']} | {row['mode']} | {row['outcomes'].get('error', 0)}/100 | {row['p50_ms'] / 1000:.2f} / {row['p95_ms'] / 1000:.2f} | {row['completed_per_second']:.2f} | {row['correct_results_per_second']:.2f} |"
            )
    elapsed = next(s["seconds"] for s in validation["steps"] if s["step"] == "full-tests")
    common = f"{tests['passed']} tests passed: {tests['unit']} unit and {tests['integration']} real Neo4j integration; zero final failures, errors or skips. Full-suite wall time: {elapsed:.2f} seconds."
    report = f"""# Stage 7A release report

**Verdict: CONDITIONAL GO for a local portfolio publication candidate only.** No production-readiness approval and no publication action. Conditions still open: owner license/rights decision, resolution or explicit acceptance of dependency advisories, actual GitHub-hosted CI and separate approval before publishing. Sustained high-concurrency HTTP reliability remains unverified.

## Executed clean-release verification

{common} All 423 historical cases were retained, with six additional publication safety/preservation cases. One historical unit hash guard was explicitly adapted to the declared documentation/configuration layout. It continues to check core implementation/data hashes; every one of the 129 integration tests is unchanged. Ruff lint and formatting passed in the release environment. The XML checker rejected any skipped or failed case rather than silently accepting partial integration coverage. After the final CLI adapter and packaging adjustments, all 300 unit tests were rerun and passed; the runtime app, source datasets, migrations and all integration test files remain unchanged.

Verification ran from the clean publication directory in a newly created Python 3.12.13 virtual environment, using `uv sync --locked` and a newly created dedicated Neo4j 5.26.32 volume. The existing download/model/image caches were reused. This demonstrates a fresh Python/database environment on this Windows host, not a fresh operating system, uncached internet bootstrap or verified Linux runner. The first D:-drive install was deliberately stopped after 447.47 seconds of cross-drive package copying; its failed attempt/log is retained. A new C:-drive environment installed in 57.77 seconds. No tests were omitted because of that setup attempt.

The three research database containers were temporarily parked for resource isolation and restored afterward. Their named volumes were not removed. Original research preservation: {preservation["original_files"]} files retain their SHA-256 checksums. The pre-release archive remains in the private research reports. Historical graph snapshots are checked separately in `reports/stage7a/research_preservation.json`.

## Real offline demonstration and smoke

The source-only demo built 12 fictional source documents, accepted {demo["source_only_build"]["accepted_facts"]} facts, published real MiniLM vectors and verified all {demo["provenance"]["facts_checked"]} fact proofs. Repeat indexing used the same cached build. Eight cases ran in three modes: 24 actual service responses. Graph/hybrid answered the qualified Priya one-, two- and three-hop chain through Atlas and PostgreSQL to AWS. The runner required an actual three-edge reasoning path. Vector's separate Atlas database example was checked. Unknown identity, bare ambiguous Lee Chen, Ivo's missing employment evidence and unsupported grammar abstained as specified. Actual response JSON, including citations and offsets, is retained. The successful demo ran on a dedicated volume verified to contain zero initial nodes, then 30 automatic factual relationships and zero curated facts. An earlier demo attempt failed its ambiguity assertion: the 12-document source subset had only one Priya, so vector correctly returned Atlas. That invalid demo expectation was corrected to the two source-backed Lee Chen identities; no retrieval rule or benchmark score was changed. The failed attempt/log remains in the research evidence. The corrected final adapter also rejects known historical database ports, and its six publication guard cases were rerun after those adapter changes.

The separate smoke rebuilt 27 source documents and {len(read("release-smoke.json")["rows"]) // 3} selected questions across all three modes: 27 actual requests. This selected nine-question subset includes six final-set cases and three calibration cases; it is a functional reproduction check, not the historical 180-question final score. The full 211-document/198-question source-only reproduction command is documented but was not rerun in Stage 7A. No historical benchmark files or scores were overwritten. In the smoke subset, vector answered 0/6 positives, graph and hybrid 4/6 each, and every mode abstained correctly on 3/3 unknowns. The two template positives remain false abstentions, not relabeled negatives. All 33 accepted smoke-build facts passed provenance validation.

## Load diagnosis and configuration correction

The original Stage 6 50-user bursts remain: vector 0/100 errors, graph 49/100, hybrid 14/100; p95 6.55/3.93/19.00 seconds and completed throughput 7.40/11.11/2.76 requests/s respectively. Completed throughput includes errors. Original error rows did not retain every underlying driver trace; a supplemental historical diagnostic identified connection acquisition failures.

Stage 7A repeated the same four calibration probes at 1/5/10/25/50 users, two waves per level, three modes: 546 requests per pool size, 1,092 measured requests total. Instrumentation recorded safe exception cause types and actual embedding lock wait/hold. Only the maximum connection pool changed, ten to 50; acquisition stayed three seconds, read retries zero, graph/hybrid budgets 20/60 seconds and graph query maximum ten seconds. Results for the 50-user levels:

| Pool | Mode | Errors /100 | p50 / p95 seconds | Completed/s incl. errors | Reference-consistent/s |
|---|---|---:|---:|---:|---:|
{chr(10).join(table)}

Reference-consistent throughput counts agreement with warmed per-mode calibration answers and known-negative abstentions; it is not an independent quality benchmark. Driver-internal active/idle occupancy was not sampled. All 56 graph and 17 hybrid failures at pool ten had ConnectionAcquisitionTimeoutError beneath DatabaseUnavailable. No measured pool-50 errors occurred at any tested user level. The release `.env.example` uses pool 50; research settings/results remain unchanged. More graph requests completed their expensive work, so graph p95 increased rather than becoming faster. At pool 50 hybrid lock-wait p95 was 15.02 seconds, versus hold p95 0.73 seconds, and host CPU reached 100%. Historical profiles found 16/18/20 database calls for one/two/three hops and a metadata Chunk scan. The unchanged proof and seal checks remain a cost.

An initial Stage 7A warm-up failed with a Bolt handshake ServiceUnavailable timeout before measured concurrency. That attempt is retained privately. A bounded readiness check preceded both recorded profiles; no retries were added to measured calls. Trials ran sequentially on one CPU, with warm-up/cache/order effects and only one before/after pair. They were service-thread bursts, not HTTP, sustained, randomized or multi-machine capacity tests. The narrow measured burst error gate improved; production high-concurrency capacity is not established. Synchronous health/readiness handlers share the API worker pool, but HTTP scheduling/event-loop delay was not measured.

## Security, package and documentation

The final secret, artifact, path and link results are in the publication manifest and audit summary. Initial Gitleaks findings were ten reviewed false positives; exact-value allowances preserve the default rules. Bandit reported 131 findings, including nine medium offline XML-parser findings and no runtime-app or high-severity findings. These remain documented trusted-input limitations. The dependency audit has **nine records, six distinct advisory IDs in Transformers 4.57.6**, across 56 audited distributions with no collection skips. This is an OPEN dependency-security gate. Fixed local cached MiniLM usage narrows exposure; it does not remediate the dependency. See [SECURITY_REVIEW.md](SECURITY_REVIEW.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

The publication has source, four migrations, fictional datasets, primary Stage 1–6 reports including failures, tests, isolated Docker settings, locked dependencies, CI, a professional README, architecture/construction/retrieval/decisions/evaluation documentation, real demo instructions and 21 interview questions. Private logs/XML, duplicate archives and large database snapshots are excluded while originals remain in research. SHA-256 inventory and package totals are recorded in [PUBLICATION_MANIFEST.md](PUBLICATION_MANIFEST.md).

The CI workflow retains lint, formatting and all unit/real integration checks, prepares the pinned model, rejects skips, and adds the actual source-only demo/smoke. The job budget is 45 minutes. The locked cross-platform Torch environment can include large CUDA dependencies even though inference uses CPU; Linux disk/download/model-startup requirements have not been measured on a hosted runner. **Hosted GitHub CI is UNVERIFIED.** No remote or hosted run exists.

## Retrieval and publication limits

The inspected Stage 5 aligned set achieved graph/hybrid 96/96 correct positives; it is not independent generalization. The Stage 6 final challenge achieved graph/hybrid 54/128 positives, vector 0/128 under the frozen new-form-incompatible answerer. Graph/hybrid false abstentions were 74/128; vector 128/128. Hybrid text chains improved to 86/128 but validated graph chains and correct answers stayed 54/128. The k=5 comparisons had zero unsupported answers; a historical k=1 partial-set failure remains. Exact denominators, source/citation counts, contamination and confidence limits are in [FINAL_EVALUATION.md](FINAL_EVALUATION.md).

Suitable as a transparent local portfolio candidate demonstrating provenance, graph construction, traversal, retrieval comparisons and failure analysis. Not ready for a public unauthenticated service, untrusted models or production reliability claims. No license was added; no Git repository, commit, remote, push, deployment or Stage 7B was created. The stopping boundary is Stage 7A.
"""
    write_doc("STAGE7A_RELEASE_REPORT.md", report)
    write_doc(
        "FINAL_PROJECT_SUMMARY.md",
        f"""# Final project summary

Stage 7A prepared a **CONDITIONAL GO portfolio candidate**. The project builds source-backed typed graphs from fictional text, validates actual multi-hop Neo4j paths, compares real local vector retrieval with graph and hybrid modes, and exposes citations and safe abstention behavior. Deterministic answer generation uses no paid generative LLM.

{common} The real source-only demo executed 24 requests; the separate selected evaluation smoke executed 27. A new Python environment and dedicated database were used with cached packages/model/image. All original research files and database snapshots are preserved and checked.

The aligned inspected Stage 5 result was graph/hybrid 96/96 positive correctness. The new Stage 6 controlled challenge gave 54/128 for graph/hybrid and 0/128 for the frozen vector answerer. Hybrid complete text-chain coverage was 86/128 without better final answers. These are internally controlled synthetic comparisons, not universal accuracy or externally administered generalization evidence.

A connection-pool-only correction reduced repeated local 50-user graph/hybrid errors from 56/100 and 17/100 to 0/100 each, while p95 remained 17.27/17.91 seconds. Original historical failures remain visible. Sustained HTTP capacity and production availability are unverified.

The package excludes credentials, private logs, database files, models and caches. Secret scans found no actual credentials after exact false-positive triage. Static findings and six distinct dependency advisory IDs remain disclosed. License/rights approval, dependency remediation or explicit risk acceptance, and a real hosted CI run remain open before public publication. No publishing, deployment or Stage 7B action occurred.

Read [STAGE7A_RELEASE_REPORT.md](STAGE7A_RELEASE_REPORT.md), [FINAL_EVALUATION.md](FINAL_EVALUATION.md), [DEMO_GUIDE.md](DEMO_GUIDE.md), [SECURITY_REVIEW.md](SECURITY_REVIEW.md) and [PUBLICATION_MANIFEST.md](PUBLICATION_MANIFEST.md).
""",
    )
    # Metadata hashes are for declared layout/config differences, never core source/data.
    manifest = json.loads((RELEASE / "PUBLICATION.json").read_text())
    for path, entry in manifest["overrides"].items():
        entry["release_sha256"] = digest(RELEASE / path)
    (RELEASE / "PUBLICATION.json").write_text(json.dumps(manifest, indent=2) + "\n")
    save(
        "final_validation_summary.json",
        {
            "tests": tests,
            "demo_smoke": summary,
            "historical_files": preservation,
            "gate": "CONDITIONAL GO portfolio only",
            "hosted_ci": "UNVERIFIED",
            "license": "NOT SELECTED",
        },
    )
    print(common)


if __name__ == "__main__":
    main()
