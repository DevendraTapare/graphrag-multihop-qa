"""Fail CI if a real integration run silently skipped checks."""

import sys
import xml.etree.ElementTree as ET


def check(path):
    cases = list(ET.parse(path).getroot().iter("testcase"))
    assert cases, "No tests executed"
    assert any("integration" in c.attrib["classname"] for c in cases), "No real integration tests"
    rejected = [
        c.attrib["name"]
        for c in cases
        if any(c.find(k) is not None for k in ("failure", "error", "skipped"))
    ]
    assert not rejected, rejected
    print(f"Verified {len(cases)} tests: no failures, errors or skips")


if __name__ == "__main__":
    check(sys.argv[1])
