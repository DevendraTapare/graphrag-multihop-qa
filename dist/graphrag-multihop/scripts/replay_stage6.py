"""Replay the frozen challenge into a new output without replacing historical scored runs."""

import argparse
import re

from scripts.evaluate_stage6 import main, stable
from scripts.stage6_support import OUT, access, read, save


def name(value):
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,50}", value) or value in {"run1", "run2"}:
        raise argparse.ArgumentTypeError("Use a new simple lowercase run name, not run1/run2")
    return value


def replay(run):
    main(run)  # Same frozen scorer, source hashes, label seal and access logging.
    access("compare replay with original scored labels/responses", OUT / "challenge_run1.json")
    old, new = read("challenge_run1.json")["queries"], read(f"challenge_{run}.json")["queries"]
    differences = [
        a["mode"] + ":" + a["id"]
        for a, b in zip(old, new, strict=True)
        if stable({k: v for k, v in a.items() if k != "wall_ms"})
        != stable({k: v for k, v in b.items() if k != "wall_ms"})
    ]
    save(
        f"replay_{run}_comparison.json",
        {"compared_to": "run1", "comparisons": len(new), "differences": differences},
    )
    if not (not differences):
        raise AssertionError(differences)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True, type=name)
    replay(parser.parse_args().run_name)
