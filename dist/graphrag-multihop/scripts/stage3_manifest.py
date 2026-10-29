"""Inventory shareable Stage 3 additions without including local credentials/caches."""

import os
from pathlib import Path

from app.graph.fixtures import ROOT

CHANGED = [
    ".env.example",
    "README.md",
    "app/core/config.py",
    "app/db/neo4j.py",
    "app/main.py",
    "app/services/validation.py",
    "docs/GRAPH_SCHEMA.md",
    "docs/PROJECT_ROADMAP.md",
    "pyproject.toml",
    "reports/README.md",
    "tests/integration/test_neo4j.py",
    "tests/unit/test_api.py",
    "uv.lock",
]


def shareable_files():
    result = set()
    for directory, dirs, files in os.walk(ROOT):
        dirs[:] = [
            d
            for d in dirs
            if d not in {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "htmlcov"}
            and not d.endswith(".egg-info")
        ]
        for name in files:
            path = Path(directory) / name
            if (
                (name.startswith(".env") and name != ".env.example")
                or name.endswith((".log", ".xml", ".pyc"))
                or name == "runtime-api-process.json"
            ):
                continue
            result.add(path.relative_to(ROOT).as_posix())
    return result


def main():
    previous = (ROOT / "reports/STAGE2_FILE_MANIFEST.md").read_text(encoding="utf-8")
    previous = previous.split("## Complete current inventory", 1)[1]
    old = {line[2:].strip() for line in previous.splitlines() if line.startswith("- ")}
    current = shareable_files() | {"docs/STAGE3_REPORT.md", "reports/stage3/FILE_MANIFEST.md"}
    if not (old <= current):
        raise AssertionError(f"Stage 2 files disappeared: {old - current}")
    new = sorted(current - old)
    lines = [
        "# Stage 3 file inventory",
        "",
        "Local secrets, environments, caches, logs, process IDs, and JUnit XML are excluded. "
        "The Stage 1–2 inventories remain historical records.",
        "",
        f"New files: **{len(new)}**. Changed existing files: **{len(CHANGED)}**. "
        f"Current shareable inventory: **{len(current)}** files.",
        "",
        "## New files",
        "",
    ]
    lines += [f"- {p}" for p in new]
    lines += ["", "## Changed existing files", ""]
    lines += [f"- {p}" for p in sorted(CHANGED)]
    lines += ["", "## Complete current inventory", ""]
    lines += [f"- {p}" for p in sorted(current)]
    (ROOT / "reports/stage3/FILE_MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print({"new": len(new), "changed": len(CHANGED), "total": len(current)})


if __name__ == "__main__":
    main()
