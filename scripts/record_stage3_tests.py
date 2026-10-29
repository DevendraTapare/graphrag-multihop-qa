"""Convert the final JUnit run into a shareable exact test inventory."""

import json
import xml.etree.ElementTree as ET

from app.graph.fixtures import ROOT


def main():
    root = ET.parse(ROOT / "reports/stage3-tests.xml").getroot()
    cases = []
    for case in root.iter("testcase"):
        status = next(
            (kind for kind in ("failure", "error", "skipped") if case.find(kind) is not None),
            "passed",
        )
        cases.append(
            {
                "class": case.get("classname"),
                "name": case.get("name"),
                "seconds": float(case.get("time", "0")),
                "status": status,
            }
        )
    result = {
        "command": "uv run pytest --run-integration -q -x --tb=short "
        "--junitxml=reports/stage3-tests.xml",
        "tests": len(cases),
        "passed": sum(c["status"] == "passed" for c in cases),
        "skipped": sum(c["status"] == "skipped" for c in cases),
        "failures": sum(c["status"] == "failure" for c in cases),
        "errors": sum(c["status"] == "error" for c in cases),
        "unit": sum("tests.unit" in c["class"] for c in cases),
        "integration": sum("tests.integration" in c["class"] for c in cases),
        "suite_seconds": sum(float(s.get("time", "0")) for s in root.iter("testsuite")),
        "cases": cases,
    }
    target = ROOT / "reports/stage3/test_results.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))


if __name__ == "__main__":
    main()
