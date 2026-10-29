"""Fail CI if a real integration run silently skipped checks."""

import sys

from defusedxml import ElementTree as ET


def check(path):
    cases = list(ET.parse(path).getroot().iter("testcase"))
    if not (cases):
        raise AssertionError("No tests executed")
    if not (any("integration" in c.attrib["classname"] for c in cases)):
        raise AssertionError("No real integration tests")
    rejected = [
        c.attrib["name"]
        for c in cases
        if any(c.find(k) is not None for k in ("failure", "error", "skipped"))
    ]
    if not (not rejected):
        raise AssertionError(rejected)
    print(f"Verified {len(cases)} tests: no failures, errors or skips")


if __name__ == "__main__":
    check(sys.argv[1])
