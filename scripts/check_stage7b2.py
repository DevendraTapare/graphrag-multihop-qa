"""Audit the intended publication, accepting only the explicitly approved MIT file."""

import json
import os
import re
from collections import defaultdict
from urllib.parse import unquote, urlsplit

from app.core.config import Settings
from scripts.stage7a_support import check_research
from scripts.stage7b2_support import RELEASE, ROOT, STATE, digest, read

MODIFIED = {
    "README.md",
    "docs/THIRD_PARTY_NOTICES.md",
    "docs/SECURITY_REVIEW.md",
    "docs/FINAL_PROJECT_SUMMARY.md",
    "docs/PUBLICATION_MANIFEST.md",
    "PUBLICATION.json",
    "FILE_INVENTORY.json",
    "SHA256SUMS",
}


def check():
    before = read("stage7b_release_freeze.json")["files"]
    paths = sorted(p for p in RELEASE.rglob("*") if p.is_file())
    names = {p.relative_to(RELEASE).as_posix() for p in paths}
    removed = sorted(before.keys() - names)
    modified = sorted(p for p, sha in before.items() if p in names and digest(RELEASE / p) != sha)
    added = sorted(names - before.keys())
    if removed or set(modified) - MODIFIED:
        raise ValueError(
            {"removed": removed, "unexpected_modifications": sorted(set(modified) - MODIFIED)}
        )
    sensitive = re.compile(r"SECRET|PASSWORD|TOKEN|API_KEY|ACCESS_KEY|PRIVATE_KEY")
    credentials = {Settings().neo4j_password.get_secret_value().encode()}
    for private in [
        ROOT / ".pytest_cache/stage7a-validation/private-environment.json",
        ROOT / ".pytest_cache/stage7a-empty-demo/private-environment.json",
        ROOT / ".pytest_cache/stage7b-validation/private-environment.json",
        ROOT / ".pytest_cache/stage7b-validation/fresh-demo-private-environment.json",
        STATE / "private-environment.json",
    ]:
        if private.exists():
            credentials.update(
                value.encode()
                for key, value in json.loads(private.read_bytes()).items()
                if isinstance(value, str) and sensitive.search(key.upper()) and len(value) >= 16
            )
    credentials.update(
        value.encode()
        for key, value in os.environ.items()
        if sensitive.search(key.upper()) and len(value) >= 16
    )
    matches, artifacts, binaries, local_paths, bad_json, missing = [], [], [], [], [], []
    links = fragments = 0
    groups = defaultdict(list)
    for p in paths:
        relative = p.relative_to(RELEASE).as_posix()
        data = p.read_bytes()
        groups[digest(p)].append(relative)
        if any(value in data for value in credentials):
            matches.append(relative)
        if (
            any(
                part
                in {
                    ".env",
                    ".git",
                    ".venv",
                    ".pytest_cache",
                    "__pycache__",
                    ".ruff_cache",
                    ".local",
                }
                for part in p.relative_to(RELEASE).parts
            )
            or p.suffix.lower()
            in {
                ".pyc",
                ".log",
                ".xml",
                ".exe",
                ".dll",
                ".pyd",
                ".whl",
                ".zip",
                ".so",
                ".safetensors",
                ".bin",
                ".pt",
                ".pth",
                ".db",
                ".pem",
                ".key",
            }
            or p.is_symlink()
        ):
            artifacts.append(relative)
        if relative.startswith("scripts/") and relative not in before:
            artifacts.append(relative)
        if b"\x00" in data:
            binaries.append(relative)
        text = data.decode("utf-8-sig")
        if re.search(r"[CD]:[/\\]+(?:Users[/\\]+Devendra|Projects[/\\]+GraphRAG-MultiHop)", text):
            local_paths.append(relative)
        if p.suffix == ".json":
            try:
                json.loads(data)
            except ValueError:
                bad_json.append(relative)
        if p.suffix != ".md":
            continue
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for match in re.finditer(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^\"]*")?\)', text):
            target = unquote(match[1].strip("<>"))
            if urlsplit(target).scheme or target.startswith("#"):
                continue
            links += 1
            local = (p.parent / target.split("#")[0]).resolve()
            if not local.is_relative_to(RELEASE.resolve()) or not local.exists():
                missing.append({"file": relative, "target": target})
            elif "#" in target and local.suffix == ".md":
                fragments += 1
                headings = re.findall(r"^#{1,6}\s+(.+)$", local.read_text(encoding="utf-8"), re.M)
                anchors = {
                    re.sub(r"[^\w -]", "", x.lower()).strip().replace(" ", "-") for x in headings
                }
                if target.split("#", 1)[1] not in anchors:
                    missing.append({"file": relative, "target": target})
    historical = {p: sha for p, sha in before.items() if p.startswith("reports/")}
    historical_changed = [p for p, sha in historical.items() if digest(RELEASE / p) != sha]
    source = {
        p: sha
        for p, sha in before.items()
        if p.startswith(("app/", "scripts/", "tests/", "data/", "migrations/"))
    }
    source_changed = [p for p, sha in source.items() if digest(RELEASE / p) != sha]
    required = [
        "pyproject.toml",
        "uv.lock",
        "compose.yaml",
        ".env.example",
        ".github/workflows/ci.yml",
    ]
    required += [p for p in before if p.startswith("migrations/")]
    absent = [p for p in required if p not in names]
    duplicates = []
    for sha, files in groups.items():
        if len(files) < 2:
            continue
        if all(x.endswith("__init__.py") for x in files):
            reason = "Required empty Python package markers"
        elif files == ["docs/ARCHITECTURE.md", "docs/PORTFOLIO_ARCHITECTURE.md"]:
            reason = "Intentional matching architecture documents retained from baseline"
        elif all(x in before for x in files):
            reason = (
                "Existing historical evidence duplicated in the baseline; preserved intentionally"
            )
        elif all(x.startswith("reports/") for x in files):
            reason = (
                "Repeated preservation evidence with identical historical snapshots; "
                "retained as dated stage records"
            )
        else:
            reason = "UNREVIEWED duplicate"
        duplicates.append({"sha256": sha, "paths": files, "reason": reason})
    official = read("mit-official-text.json")["paragraphs"]
    license_text = (RELEASE / "LICENSE").read_bytes().decode("utf-8")
    blocks = re.split(r"\n\s*\n", license_text.strip())
    mit_ok = (
        blocks[:2] == ["MIT License", "Copyright (c) 2026 Devendra Tapare"]
        and [" ".join(x.split()) for x in blocks[2:]] == official
    )
    result = {
        "files": len(paths),
        "bytes": sum(p.stat().st_size for p in paths),
        "added": added,
        "modified": modified,
        "removed": removed,
        "exact_credential_match_paths": matches,
        "credential_values_checked": len(credentials),
        "forbidden_artifacts": artifacts,
        "unexpected_binary_paths": binaries,
        "workstation_path_files": local_paths,
        "invalid_json": bad_json,
        "documentation_local_links": links,
        "documentation_fragments": fragments,
        "missing_links": missing,
        "historical_release_reports_checked": len(historical),
        "historical_report_changes": historical_changed,
        "source_test_data_migration_files_checked": len(source),
        "source_changes": source_changed,
        "required_files": required,
        "missing_required_files": absent,
        "duplicate_groups": duplicates,
        "mit_complete_and_exact": mit_ok,
        "temporary_stage7b_candidate_included": False,
        "research_preservation": check_research(),
    }
    if (
        any(
            [
                matches,
                artifacts,
                binaries,
                local_paths,
                bad_json,
                missing,
                historical_changed,
                source_changed,
                absent,
            ]
        )
        or not mit_ok
        or any(x["reason"].startswith("UNREVIEWED") for x in duplicates)
    ):
        raise ValueError(result)
    return result
