"""Assemble the publication without rewriting any frozen research file."""

import json
import shutil

from scripts.stage7a_support import OUT, RELEASE, ROOT, check_research, digest, read

OMIT_NAMES = {
    "challenge_run1.json",
    "challenge_run2.json",
    "aligned_snapshot.json",
    "graph_snapshot.json",
    "challenge_snapshot.json",
    "hybrid_no_reranking_metrics.json",
    "label_access.jsonl",
    "runtime-api-process.json",
}


def portable(raw):
    text = raw.decode("utf-8")
    for prefix in (
        "D:\\\\Projects\\\\GraphRAG-MultiHop",
        "D:\\Projects\\GraphRAG-MultiHop",
        "D:/Projects/GraphRAG-MultiHop",
        "C:\\\\Users\\\\Devendra",
        "C:\\Users\\Devendra",
        "C:/Users/Devendra",
    ):
        text = text.replace(prefix, "<research-workspace>")
    return text.encode("utf-8")


def copy(source, relative):
    target = RELEASE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def assemble():
    check_research()
    if RELEASE.exists():
        raise ValueError(
            "Publication already exists; update explicitly without rebuilding evidence"
        )
    RELEASE.mkdir(parents=True)
    original = read("research_freeze.json")["files"]
    omitted, changed = {}, {}
    for relative, sha in original.items():
        path = ROOT / relative
        if path.suffix in {".zip", ".log", ".xml", ".jsonl"} or path.name in OMIT_NAMES:
            omitted[relative] = {
                "source_sha256": sha,
                "reason": "Private log or redundant research archive/snapshot; original retained",
            }
            continue
        copy(path, relative)
        if relative.startswith(("docs/", "reports/", "infra/")):
            raw = (RELEASE / relative).read_bytes()
            clean = portable(raw)
            if clean != raw:
                (RELEASE / relative).write_bytes(clean)
                changed[relative] = {
                    "source_sha256": sha,
                    "release_sha256": digest(RELEASE / relative),
                    "reason": "Remove workstation-specific absolute paths",
                }
    # New code is copied explicitly; no root venv, env, cache or generated state is visited.
    for relative in ("scripts/portfolio.py",):
        copy(ROOT / relative, relative)
    copy(ROOT / "README.md", "docs/history/README_STAGE6.md")
    copy(ROOT / "docs/ARCHITECTURE.md", "docs/history/ARCHITECTURE_STAGE1.md")
    (RELEASE / "docs/history/README_STAGE6.md").write_bytes(
        portable((ROOT / "README.md").read_bytes())
    )
    for path in (ROOT / "docs").glob("*.md"):
        if path.relative_to(ROOT).as_posix() not in original:
            copy(path, path.relative_to(ROOT))
    copy(ROOT / "docs/PORTFOLIO_ARCHITECTURE.md", "docs/ARCHITECTURE.md")
    copy(OUT / "publication_sources/README.md", "README.md")
    # New loopback ports/project prevent accidental contact with historical volumes.
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    compose = compose.replace("name: graphrag-multihop", "name: graphrag-portfolio")
    compose = compose.replace(":-7474", ":-37477").replace(":-7687", ":-37690")
    (RELEASE / "compose.yaml").write_text(compose, encoding="utf-8")
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    env = env.replace("127.0.0.1:7687", "127.0.0.1:37690")
    env = env.replace("NEO4J_HTTP_PORT=7474", "NEO4J_HTTP_PORT=37477")
    env = env.replace("NEO4J_BOLT_PORT=7687", "NEO4J_BOLT_PORT=37690")
    env = env.replace("NEO4J_POOL_SIZE=10", "NEO4J_POOL_SIZE=50")
    (RELEASE / ".env.example").write_text(env, encoding="utf-8")
    (RELEASE / ".gitignore").write_text(
        (ROOT / ".gitignore").read_text() + "\n.local/\ndist/\n*.pem\n*.key\n", encoding="utf-8"
    )
    # The original guard has an explicit, narrow publication-layout adaptation.
    guard = RELEASE / "tests/unit/test_graph_rag.py"
    text = guard.read_text(encoding="utf-8")
    old = (
        "            assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, path"
    )
    new = """            publication = json.loads((root / "PUBLICATION.json").read_text())
            omission = publication["omissions"].get(path)
            change = publication["overrides"].get(path)
            if omission:
                assert path.startswith("reports/"), path
                assert omission["source_sha256"] == digest, path
                assert not (root / path).exists(), path
            elif change:
                assert path.startswith(("docs/", "reports/", "infra/")) or path in {
                    ".gitignore", "compose.yaml"
                }, path
                assert change["source_sha256"] == digest, path
                assert hashlib.sha256((root / path).read_bytes()).hexdigest() == change[
                    "release_sha256"
                ], path
            else:
                assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, path"""
    if text.count(old) != 1:
        raise ValueError("Historical guard changed")
    guard.write_text(text.replace(old, new), encoding="utf-8")
    for relative in (
        ".gitignore",
        ".env.example",
        "compose.yaml",
        "README.md",
        "docs/ARCHITECTURE.md",
        "tests/unit/test_graph_rag.py",
    ):
        changed[relative] = {
            "source_sha256": original[relative],
            "release_sha256": digest(RELEASE / relative),
            "reason": "Explicit publication layout/configuration; guard preserves core/data checks",
        }
    manifest = {
        "stage": "7A",
        "portfolio_only": True,
        "license_selected": False,
        "original_files": len(original),
        "omissions": omitted,
        "overrides": changed,
        "core_source_hashes": {
            p: h for p, h in original.items() if p.startswith(("app/", "data/", "migrations/"))
        },
        "note": (
            "Research preserved. One historical unit hash guard adapted for declared "
            "documentation/configuration changes; all integration tests unchanged."
        ),
    }
    (RELEASE / "PUBLICATION.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    check_research()
    print(
        json.dumps(
            {
                "directory": str(RELEASE),
                "initial_files": sum(p.is_file() for p in RELEASE.rglob("*")),
                "omissions": len(omitted),
            }
        )
    )


if __name__ == "__main__":
    assemble()
