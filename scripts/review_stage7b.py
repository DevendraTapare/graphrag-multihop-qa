"""Record per-finding security decisions without rewriting historical audit evidence."""

# Long Markdown prose is emitted as a document, not executable statements.
# ruff: noqa: E501

import ast
import json
import zipfile
from collections import Counter

from scripts.stage7b_support import OUT, ROOT, save


def bandit_review():
    original = json.loads((ROOT / "reports/stage7a/bandit-final.json").read_bytes())
    final = json.loads((OUT / "bandit.json").read_bytes())
    remaining = {(r["filename"].replace("\\", "/"), r["test_id"]): [] for r in final["results"]}
    for result in final["results"]:
        remaining[result["filename"].replace("\\", "/"), result["test_id"]].append(
            result["line_number"]
        )
    rows = []
    for number, result in enumerate(original["results"], 1):
        path = result["filename"].replace("\\", "/")
        line = result["line_number"]
        rule = result["test_id"]
        with zipfile.ZipFile(OUT / "stage7a_release_before_security.zip") as archive:
            tree = ast.parse(archive.read(path).decode("utf-8"))
        functions = [
            n
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.lineno <= line <= n.end_lineno
        ]
        function = (
            min(functions, key=lambda n: n.end_lineno - n.lineno).name
            if functions
            else "module import"
        )
        node = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.Assert) and n.lineno == line), None
        )
        behavior = ast.unparse(node) if node else result["code"].strip().replace("\n", " | ")
        reachable = f"Local developer script: {function}; no API request path calls this script."
        if rule == "B101":
            classification = "Real verification/preservation issue under python -O; fixed"
            reason = (
                "The condition protects evidence, a workflow boundary, or a verification claim. "
                "Optimized Python removed the assertion. Explicit conditional AssertionError "
                "now preserves the original condition and message, including under -O."
            )
            mitigation = "Applied explicit conditional exception; no suppression."
        elif rule in {"B314", "B405"}:
            classification = (
                "Real unnecessary XML parsing exposure; fixed"
                if rule == "B314"
                else "Import warning; associated parser hardened"
            )
            reason = (
                "Reads locally generated JUnit XML, not HTTP input. Local file replacement or "
                "an externally supplied CI artifact could introduce entities. The six modules "
                "now use defusedxml; a harmless entity-declaration regression is rejected."
            )
            mitigation = "Applied defusedxml 0.7.1 in the dev dependency group; no suppression."
        elif rule == "B311":
            classification = "False positive for cryptographic use; retained"
            reason = "Seeded Random(602910) creates reproducible fictional benchmark names; it creates no secrets, tokens or passwords."
            mitigation = "Keep deterministic data generation. Use secrets for credentials; historical dataset bytes remain unchanged."
        elif rule == "B404":
            classification = "Import warning; no independent vulnerability; retained"
            reason = "subprocess import alone does not execute a process. Each associated call is separately reviewed below."
            mitigation = "Keep the import; review callers when commands or input sources change."
        elif rule == "B603":
            classification = "False positive for command injection in current call sites; retained"
            reason = (
                "Calls use argument lists with shell=False (default). Compose actions come from "
                "literal local call sites, not document/question input. API children use "
                "sys.executable, fixed module/loopback arguments and locally allocated ports."
            )
            mitigation = (
                "Keep shell=False and fixed argv; do not connect these wrappers to untrusted input."
            )
        elif rule == "B607":
            classification = "Real conditional local PATH substitution risk; accepted low residual"
            reason = (
                "The local Docker CLI is found through PATH. An attacker controlling PATH or "
                "an earlier writable executable directory could replace it. No remote/API "
                "input chooses the executable. A portable absolute Docker path is not assumed."
            )
            mitigation = "Run only with a trusted Docker installation and PATH in the trusted local workspace. These legacy recovery scripts are not the published demo workflow."
        else:
            raise ValueError(rule)
        rows.append(
            {
                "number": number,
                "file": path,
                "line": line,
                "rule": rule,
                "severity": result["issue_severity"],
                "confidence": result["issue_confidence"],
                "behavior": behavior,
                "reachable": reachable,
                "classification": classification,
                "rationale": reason,
                "remediation": mitigation,
                "final_lines": remaining.get((path, rule), []),
            }
        )
    save(
        "bandit-review.json",
        {
            "scope": "Every original Stage 7A finding; final scan includes app/scripts, not tests or dependencies",
            "original_findings": len(rows),
            "final_findings": len(final["results"]),
            "original_by_rule": dict(Counter(r["rule"] for r in rows)),
            "final_by_rule": dict(Counter(r["test_id"] for r in final["results"])),
            "findings": rows,
        },
    )
    lines = [
        "# Every Bandit finding and its disposition",
        "",
        "Line numbers refer to the Stage 7A input. Final locations for retained findings are in the JSON review. "
        "Every finding is reachable only through a local developer tool or its import; none is on an application request path. "
        "Historical tools can write reports or operate on research databases and must not be used as the clean demo workflow. "
        "No Bandit rule was suppressed. See `bandit-review.json` for code context, exact per-row rationale and remediation.",
        "",
        "| # | File:line | Rule | Severity/confidence | Assessment and remediation |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        text = row["classification"] + ". " + row["remediation"]
        lines.append(
            f"| {row['number']} | `{row['file']}:{row['line']}` | {row['rule']} | {row['severity']}/{row['confidence']} | {text} |"
        )
    (OUT / "BANDIT_REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    bandit_review()
