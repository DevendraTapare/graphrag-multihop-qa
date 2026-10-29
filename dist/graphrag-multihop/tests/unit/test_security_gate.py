"""Exercise the release gate against unsafe XML and misleading test results."""

import subprocess
import sys

import pytest
from defusedxml.common import EntitiesForbidden

from scripts.check_ci_results import check


def test_normal_junit_passes(tmp_path):
    path = tmp_path / "tests.xml"
    path.write_text(
        '<testsuite><testcase classname="tests.integration.graph" name="ok"/></testsuite>'
    )
    check(path)


def test_xml_entities_are_rejected(tmp_path):
    path = tmp_path / "tests.xml"
    path.write_text('<!DOCTYPE x [<!ENTITY x "small harmless entity">]><testsuite>&x;</testsuite>')
    with pytest.raises(EntitiesForbidden):
        check(path)


@pytest.mark.parametrize("status", ["failure", "error", "skipped"])
def test_optimized_python_rejects_bad_results(tmp_path, status):
    path = tmp_path / "tests.xml"
    path.write_text(
        '<testsuite><testcase classname="tests.integration.graph" name="bad">'
        f"<{status}/></testcase></testsuite>"
    )
    result = subprocess.run(
        [sys.executable, "-O", "-m", "scripts.check_ci_results", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "AssertionError" in result.stderr


@pytest.mark.parametrize(
    "content,reason",
    [
        ("<testsuite/>", "No tests executed"),
        (
            '<testsuite><testcase classname="tests.unit.x" name="ok"/></testsuite>',
            "No real integration tests",
        ),
    ],
)
def test_incomplete_results_are_rejected(tmp_path, content, reason):
    path = tmp_path / "tests.xml"
    path.write_text(content)
    with pytest.raises(AssertionError, match=reason):
        check(path)
