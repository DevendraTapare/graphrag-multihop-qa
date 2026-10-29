"""Check the entire publication payload, including real credential exclusion."""

import json
import os
import re
from collections import Counter
from urllib.parse import unquote, urlsplit

from app.core.config import Settings
from scripts.stage7a_support import check_research
from scripts.stage7b_support import OUT, ROOT, STATE, digest


def check(directory):
    files = sorted(p for p in directory.rglob("*") if p.is_file())
    secrets = {Settings().neo4j_password.get_secret_value().encode()}
    sensitive_name = re.compile(r"(?:SECRET|PASSWORD|TOKEN|API_KEY|ACCESS_KEY|PRIVATE_KEY)")
    secrets.update(
        value.encode()
        for key, value in os.environ.items()
        if sensitive_name.search(key.upper()) and len(value) >= 16
    )
    for private in [
        ROOT / ".pytest_cache/stage7a-validation/private-environment.json",
        ROOT / ".pytest_cache/stage7a-empty-demo/private-environment.json",
        STATE / "private-environment.json",
        STATE / "fresh-demo-private-environment.json",
    ]:
        if private.exists():
            private_values = json.loads(private.read_bytes())
            secrets.update(
                value.encode()
                for key, value in private_values.items()
                if isinstance(value, str)
                and sensitive_name.search(key.upper())
                and len(value) >= 16
            )
    matches, forbidden, binaries, paths, invalid_json, links, missing = [], [], [], [], [], 0, []
    for path in files:
        relative = path.relative_to(directory).as_posix()
        data = path.read_bytes()
        if any(secret in data for secret in secrets):
            matches.append(relative)
        if (
            path.is_symlink()
            or any(
                x
                in {
                    ".env",
                    ".venv",
                    "__pycache__",
                    ".pytest_cache",
                    ".ruff_cache",
                    ".git",
                    ".local",
                }
                for x in path.relative_to(directory).parts
            )
            or path.suffix.lower()
            in {
                ".pyc",
                ".bin",
                ".safetensors",
                ".pem",
                ".key",
                ".db",
                ".log",
                ".xml",
                ".zip",
                ".exe",
                ".dll",
                ".pyd",
                ".so",
                ".pdf",
            }
            or path.name.upper().startswith("LICENSE")
        ):
            forbidden.append(relative)
        if b"\x00" in data:
            binaries.append(relative)
        text = data.decode("utf-8-sig")
        if re.search(r"[CD]:[/\\]+(?:Users[/\\]+Devendra|Projects[/\\]+GraphRAG-MultiHop)", text):
            paths.append(relative)
        if path.suffix == ".json":
            try:
                json.loads(data)
            except ValueError:
                invalid_json.append(relative)
        if path.suffix != ".md":
            continue
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for match in re.finditer(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^\"]*")?\)', text):
            target = unquote(match[1].strip("<>"))
            if urlsplit(target).scheme or target.startswith("#"):
                continue
            links += 1
            local = (path.parent / target.split("#")[0]).resolve()
            if not local.is_relative_to(directory.resolve()) or not local.exists():
                missing.append({"file": relative, "target": target})
    before = json.loads((OUT / "stage7a_release_freeze.json").read_bytes())["files"]
    historical = {p: sha for p, sha in before.items() if p.startswith("reports/")}
    report_changes = [p for p, sha in historical.items() if digest(directory / p) != sha]
    manifest = json.loads((directory / "PUBLICATION.json").read_bytes())
    core_changes = [
        p for p, sha in manifest["core_source_hashes"].items() if digest(directory / p) != sha
    ]
    integration_changes = [
        p
        for p, sha in before.items()
        if p.startswith("tests/integration/") and digest(directory / p) != sha
    ]
    result = {
        "files": len(files),
        "bytes": sum(p.stat().st_size for p in files),
        "exact_credential_match_paths": matches,
        "credential_values_checked": len(secrets),
        "forbidden_artifacts": forbidden,
        "unexpected_binary_paths": binaries,
        "workstation_path_files": paths,
        "invalid_json": invalid_json,
        "documentation_local_links": links,
        "missing_links": missing,
        "historical_release_reports_checked": len(historical),
        "historical_report_changes": report_changes,
        "core_source_files_checked": len(manifest["core_source_hashes"]),
        "core_source_changes": core_changes,
        "integration_source_changes": integration_changes,
        "research_preservation": check_research(),
        "file_types": dict(Counter(p.suffix or "<none>" for p in files)),
    }
    if any(
        [
            matches,
            forbidden,
            binaries,
            paths,
            invalid_json,
            missing,
            report_changes,
            core_changes,
            integration_changes,
        ]
    ):
        raise ValueError(result)
    return result
