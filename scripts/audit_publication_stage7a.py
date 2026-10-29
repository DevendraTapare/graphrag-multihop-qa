"""Read-only artifact, exact-secret, path and documentation checks."""

import json
import re
from collections import Counter
from urllib.parse import unquote, urlsplit

from app.core.config import Settings
from scripts.stage7a_support import RELEASE, ROOT, check_research, read, save


def main():
    secret = Settings().neo4j_password.get_secret_value().encode()
    private = ROOT / ".pytest_cache/stage7a-validation/private-environment.json"
    release_secret = json.loads(private.read_text())["NEO4J_PASSWORD"].encode()
    # Search the historical inventory and every publication file. Never print a value.
    originals = list(read("research_freeze.json")["files"])
    original_matches = [p for p in originals if secret in (ROOT / p).read_bytes()]
    files = sorted(p for p in RELEASE.rglob("*") if p.is_file())
    release_matches = [p.relative_to(RELEASE).as_posix() for p in files if secret in p.read_bytes()]
    fresh_matches = [
        p.relative_to(RELEASE).as_posix() for p in files if release_secret in p.read_bytes()
    ]
    empty_demo_private = ROOT / ".pytest_cache/stage7a-empty-demo/private-environment.json"
    if empty_demo_private.exists():
        other = json.loads(empty_demo_private.read_text())["NEO4J_PASSWORD"].encode()
        fresh_matches.extend(
            p.relative_to(RELEASE).as_posix() for p in files if other in p.read_bytes()
        )
    forbidden_names = {".env", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".git"}
    forbidden_suffix = {
        ".pyc",
        ".bin",
        ".safetensors",
        ".pem",
        ".key",
        ".db",
        ".log",
        ".xml",
        ".zip",
    }
    forbidden = [
        p.relative_to(RELEASE).as_posix()
        for p in RELEASE.rglob("*")
        if p.name in forbidden_names or p.suffix in forbidden_suffix
    ]
    paths = []
    for p in files:
        if p.suffix not in {
            ".md",
            ".json",
            ".csv",
            ".yml",
            ".yaml",
            ".toml",
            ".example",
            ".py",
            ".cypher",
        }:
            continue
        text = p.read_text(encoding="utf-8")
        if re.search(
            r"(?:[CD]:[/\\]+(?:Users[/\\]+Devendra|Projects[/\\]+GraphRAG-MultiHop))", text
        ):
            paths.append(p.relative_to(RELEASE).as_posix())
    links, fragments, missing = 0, 0, []
    for p in files:
        if p.suffix != ".md":
            continue
        text = re.sub(r"```.*?```", "", p.read_text(encoding="utf-8"), flags=re.S)
        for match in re.finditer(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", text):
            target = unquote(match[1].strip("<>"))
            if urlsplit(target).scheme or target.startswith("#"):
                continue
            links += 1
            local = (p.parent / target.split("#")[0]).resolve()
            if not local.is_relative_to(RELEASE.resolve()) or not local.exists():
                missing.append({"file": p.relative_to(RELEASE).as_posix(), "target": target})
            elif "#" in target and local.suffix == ".md":
                fragments += 1
                headings = re.findall(r"^#{1,6}\s+(.+)$", local.read_text(encoding="utf-8"), re.M)
                anchors = {
                    re.sub(r"[^\w -]", "", h.lower()).strip().replace(" ", "-") for h in headings
                }
                if target.split("#", 1)[1] not in anchors:
                    missing.append({"file": p.relative_to(RELEASE).as_posix(), "target": target})
    result = {
        "release_files": len(files),
        "release_bytes": sum(p.stat().st_size for p in files),
        "file_types": dict(Counter(p.suffix or "<none>" for p in files)),
        "research_secret_locations": {
            "private_env_present": (ROOT / ".env").exists(),
            "shareable_evidence_matches": original_matches,
        },
        "release_actual_research_secret_matches": release_matches,
        "release_actual_fresh_secret_matches": fresh_matches,
        "forbidden_artifacts": forbidden,
        "workstation_path_files": paths,
        "documentation_local_links": links,
        "documentation_fragments": fragments,
        "missing_links": missing,
        "research_preservation": check_research(),
    }
    save("publication_audit.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
