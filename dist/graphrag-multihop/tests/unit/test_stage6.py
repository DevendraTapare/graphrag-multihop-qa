"""Independence and reporting contracts that protect the controlled challenge."""

import ast
import json
from pathlib import Path

import pytest

from scripts.check_ci_results import check
from scripts.evaluate_stage6 import stable, summary
from scripts.stage6_runtime import URI


@pytest.mark.parametrize("filename", ["scripts/build_stage6.py", "scripts/stage6_runtime.py"])
def test_challenge_runtime_and_builder_do_not_read_labels(filename):
    source = Path(filename).read_text()
    tree = ast.parse(source)
    imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert all("evaluation" not in x and "dataset" not in x for x in imports)
    strings = [
        n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    assert not any(
        "labels.json" in s or "world.json" in s or "expected_answer" in s for s in strings
    )


def test_repeat_comparison_keeps_answers_evidence_and_scores():
    first = {
        "answer": "Fictional",
        "score": 0.9,
        "latency_ms": {"total": 1},
        "citations": [{"quote": "A fact", "request_id": "one"}],
    }
    second = json.loads(json.dumps(first))
    second["latency_ms"]["total"] = 20
    second["citations"][0]["request_id"] = "two"
    assert stable(first) == stable(second)
    second["citations"][0]["quote"] = "Other fact"
    assert stable(first) != stable(second)


@pytest.mark.parametrize("bad", ["skipped", "failure", "error"])
def test_ci_rejects_incomplete_real_test_runs(tmp_path, bad):
    path = tmp_path / "results.xml"
    path.write_text(
        f'<testsuite><testcase classname="tests.integration.check" name="security">'
        f"<{bad}/></testcase></testsuite>"
    )
    with pytest.raises(AssertionError):
        check(path)


def test_empty_category_does_not_report_perfect_citations():
    value = summary([])
    assert value["citation_correctness"] is None
    assert value["answer_exact_match"] is None


def test_challenge_endpoint_is_separate_from_historical_ports():
    assert URI == "bolt://127.0.0.1:27689"
