"""Record the redistribution boundary before applying the approved MIT notice."""

# Complete Markdown paragraphs and tables are emitted as document text.
# ruff: noqa: E501

import json
import re
import textwrap
from collections import Counter

from scripts.stage7b2_support import OUT, RELEASE, digest, read, save, update_publication


def inventory():
    packages = read("package-rights-evidence.json")
    wheel_path = OUT / "wheel-rights-review.json"
    wheel_evidence = {p["name"]: p for p in read(wheel_path.name)} if wheel_path.exists() else {}
    if any(p.get("error") for p in packages):
        raise ValueError("Package rights metadata unavailable; review before proceeding")
    fixes = {
        "colorama": "BSD-3-Clause",
        "jinja2": "BSD-3-Clause",
        "markdown-it-py": "MIT",
        "mdurl": "MIT",
        "safetensors": "Apache-2.0",
        "tokenizers": "Apache-2.0",
        "scipy": "BSD-3-Clause (project; bundled components retain separate notices)",
        "defusedxml": "PSF license version 2 (metadata uses PSFL)",
        "nvidia-cuda-runtime": "NVIDIA CUDA Software License Agreement and supplement (inspected wheel)",
        "nvidia-cudnn-cu13": "NVIDIA SDK License Agreement and cuDNN supplement (inspected wheel)",
        "nvidia-nccl-cu13": "BSD-3-Clause main notice; additional NVTX component reference",
        "nvidia-nvshmem-cu13": "NVIDIA CUDA Software License Agreement and supplement (inspected wheel)",
        "nvidia-nvtx": "Apache-2.0 WITH LLVM-exception (inspected wheel; metadata classifier conflicts)",
    }
    rows = []
    for package in packages:
        if package.get("first_party"):
            continue
        name = package["name"]
        expression = package.get("license_expression")
        legacy = (package.get("license") or "").strip()
        basis = "Publisher's exact-version PyPI metadata"
        if name in fixes:
            license_name = fixes[name]
            if name.startswith("nvidia-"):
                if not wheel_evidence.get(name, {}).get("notices"):
                    raise ValueError("Missing exact wheel license evidence")
                basis += "; exact PyPI wheel license members inspected with bounded HTTP ranges, CRC checked"
            else:
                basis += (
                    "; main installed artifact license inspected"
                    if name != "tokenizers"
                    else "; exact upstream v0.23.3 LICENSE inspected"
                )
        elif expression:
            license_name = expression
        elif legacy and len(legacy) < 100:
            license_name = legacy
        elif package.get("license_classifiers"):
            license_name = "; ".join(package["license_classifiers"]).replace(
                "License :: OSI Approved :: ", ""
            )
        else:
            license_name = "Not declared in reviewed package metadata; exact wheel terms unverified"
        unresolved = license_name.startswith("Not declared")
        restriction = "Keep upstream terms and notices when installing; this project's MIT does not relicense this package."
        if name == "nvidia-cudnn-cu13":
            restriction += " The inspected cuDNN supplement limits application development to systems with NVIDIA GPUs."
        if name.startswith(("nvidia-", "cuda-")):
            restriction += " Review the exact vendor conditions before installation/use on other platforms or any bundled redistribution."
        action = "No package code/binary is bundled. Before any future redistribution, inspect the exact wheel's LICENSE/NOTICE and satisfy its terms."
        if unresolved:
            action = "Exact binary redistribution terms require further verification before bundling. The dependency is external and separable from this MIT source package."
        rows.append(
            {
                "asset": name,
                "version": package["version"],
                "license": license_name,
                "source": package["source"],
                "verification_basis": basis,
                "redistributed": False,
                "scope": "Installation reference in uv.lock; no package source or wheel bundled",
                "installed_on_verification_host": package["installed_for_verification"],
                "required_notices": "Preserve upstream copyright, license and applicable component/NOTICE files; see license family guidance",
                "known_restrictions": restriction,
                "action_required": action,
                "future_binary_terms_unresolved": unresolved,
                "exact_wheel_evidence": (
                    {
                        **wheel_evidence[name],
                        "notices": [
                            {k: v for k, v in notice.items() if k != "opening"}
                            for notice in wheel_evidence[name].get("notices", [])
                        ],
                    }
                    if name in wheel_evidence
                    else None
                ),
                "license_source": (
                    "https://github.com/huggingface/tokenizers/blob/v0.23.3/LICENSE"
                    if name == "tokenizers"
                    else package["source"]
                ),
                "reviewed_artifact_notice_files": package["artifact_licenses"],
            }
        )
    files = [p for p in RELEASE.rglob("*") if p.is_file()]
    forbidden = [
        p.relative_to(RELEASE).as_posix()
        for p in files
        if p.suffix.lower()
        in {
            ".exe",
            ".dll",
            ".pyd",
            ".so",
            ".whl",
            ".safetensors",
            ".bin",
            ".pt",
            ".pth",
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".gif",
            ".webp",
            ".pdf",
            ".zip",
        }
    ]
    if forbidden:
        raise ValueError("Unexpected binary/model/media requires a separate rights review")
    reviewed = {
        "as_of": "2026-10-29",
        "scope": "Current source-only clean release",
        "input_files": read("stage7b_release_freeze.json")["file_count"],
        "file_types_at_review": dict(Counter(p.suffix or "<none>" for p in files)),
        "registry_packages": len(rows),
        "installed_packages": sum(r["installed_on_verification_host"] for r in rows),
        "packages": rows,
        "included_rights_blockers": [],
        "first_party_basis": "Project-controlled source and fictional fixture generation history plus explicit owner authority/approval; not an independent proof of ownership of every line",
        "copied_third_party_code_identified": [],
        "external_benchmark_data_identified": [],
        "bundled_models_tokenizers_images_or_dependencies": [],
        "included_third_party_notices": [
            "reports/stage7a/dependency_metadata.json",
            "reports/stage7b/dependency-metadata.json",
        ],
        "notice_disposition": "Existing upstream license/copyright metadata and excerpts remain unchanged under their original terms",
        "model_license_basis": "Pinned MiniLM model card declares apache-2.0; standalone LICENSE URL returned 404. Model/tokenizer files are not bundled.",
        "future_binary_questions": [
            r["asset"] for r in rows if r["future_binary_terms_unresolved"]
        ],
    }
    save("third-party-rights.json", reviewed)
    return reviewed


def document(rights):
    rows = []
    for p in rights["packages"]:
        note = (
            "Verify exact wheel terms before bundling"
            if p["future_binary_terms_unresolved"]
            else "Retain exact upstream license/component notices before bundling"
        )
        rows.append(
            f"| [{p['asset']}]({p['source']}) | {p['version']} | {p['license']} | External installation reference | {note} |"
        )
    text = (
        """# Third-party licenses and rights inventory

Reviewed 29 October 2026. Project license: **MIT**. Copyright holder: **Devendra Tapare**. Year: **2026**. The approved [LICENSE](../LICENSE) covers only first-party code and original material the owner owns or has authority to license. Third-party dependencies, datasets, models, assets and retained upstream notices keep their own terms. Their installation or mention does not make them MIT-licensed project material.

The review covered all 348 Stage 7B.1 publication files, Python source/imports and attribution markers, the full lock, Docker/CI configuration, every data directory, Markdown media/links and existing generated reports. No vendored dependency source, copied-source attribution block, external benchmark dataset, bundled image/font/screenshot, installed environment, tokenizer artifact or model weight was identified. This relies on project construction history and the owner's authority for original material; it is not an independent ownership certification of every line.

## Included material and installation references

| Asset | Version/source and verified license | Redistributed here? | Notice/restriction and action |
|---|---|---|---|
| First-party Python, tests, migrations, configs and original docs | Project history; owner-approved MIT, 2026 Devendra Tapare | Yes | Preserve the project MIT notice; do not apply it to third-party portions. |
| Fictional corpora, registry, labels and generated evaluations | Project-controlled fictional fixtures and dataset-authoring scripts; MIT only to the extent owned/authorized | Yes | Preserve provenance and negative results. No external benchmark corpus was identified. Product/technology names do not transfer third-party trademark rights. |
| Existing dependency license/copyright metadata | Unchanged `reports/stage7a/dependency_metadata.json` and `reports/stage7b/dependency-metadata.json` | Yes, as notices/metadata | Upstream notices and excerpts remain under their original terms and were not removed or relabeled MIT. |
| Markdown/Mermaid diagram definitions | Original project diagram source | Yes | Covered only as authorized original material. No Mermaid JS or third-party bitmap asset is bundled. |
| Python dependency manifests and uv.lock | Exact publisher metadata and artifact license files; per-package table below | References/metadata only | No Python dependency source, wheel or native binary is bundled. Exact package terms remain separate. |
| Neo4j Community | 5.26.32-community; [versioned GPL v3 LICENSE](https://github.com/neo4j/neo4j/blob/5.26.32/LICENSE.txt) | Container reference only | Downloaded separately through Docker; not relicensed MIT. Any future binary distribution requires its GPL/corresponding-source review. |
| all-MiniLM-L6-v2 | [Pinned model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/README.md), revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41, declares Apache-2.0 | Model/tokenizer reference only | Explicit preparation downloads the trusted revision separately; inference is cache-only. Model card licensing does not relicense its training datasets. No standalone LICENSE file was found at that revision (404); revisit notices before bundling weights. |
| actions/checkout | CI commit 3d3c42e5aac5ba805825da76410c181273ba90b1; [MIT](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/LICENSE) | CI reference only | Preserve its license if ever copying action code. No action code is vendored. Hosted execution is UNVERIFIED. |
| astral-sh/setup-uv | CI commit c771a70e6277c0a99b617c7a806ffedaca235ff9; [MIT](https://github.com/astral-sh/setup-uv/blob/c771a70e6277c0a99b617c7a806ffedaca235ff9/LICENSE) | CI reference only | External action download; no action code bundled. |
| uv | 0.11.23; [MIT](https://github.com/astral-sh/uv/blob/0.11.23/LICENSE-MIT) OR [Apache-2.0](https://github.com/astral-sh/uv/blob/0.11.23/LICENSE-APACHE) | Tool reference only | Installed separately; its license is not replaced by the project license. |
| Docker Desktop | Separately installed host tool; [Docker's own terms](https://docs.docker.com/subscription-billing/desktop-license/) | No | The project does not grant Docker Desktop use or redistribution rights. |

Python itself and system/container tooling are not included in the publication. Existing cached dependencies/model/image were reused for local verification. Downloaded license texts and private review helpers remain outside the publication. No upstream Python package or model was copied into this repository to perform the review.

## Every locked Python package

There are 79 registry packages and one local project entry. Sixty are installed on this Windows verification host. The other 19 are cross-platform lock entries, including optional CUDA/Linux dependencies. Their presence is not a statement that the CPU demo uses them. Each linked source is publisher metadata for the exact locked version. Main artifact licenses were checked for ambiguous installed metadata; exact expressions with multiple licenses are preserved rather than flattened. Artifact notice-file paths and hashes, declaration basis and per-item action/restrictions are in [third-party-rights.json](../reports/stage7b2/third-party-rights.json).

| Package/source | Locked version | Verified declaration or stated uncertainty | Distribution status | Required action |
|---|---|---|---|---|
"""
        + "\n".join(rows)
        + """

## Notice requirements and unresolved questions

If third-party code or binaries are redistributed later, retain their exact copyright, license and component notices. MIT requires its notice; BSD/ISC variants retain their stated notices/conditions. [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) includes license, modification and applicable NOTICE requirements and does not grant trademark rights. [MPL-2.0](https://www.mozilla.org/en-US/MPL/2.0/) keeps covered-source obligations for its covered portions. PSF/Python and combined-license packages require their exact agreements, not an assumed blanket MIT substitute. These are review pointers; the referenced licenses control.

Several CUDA package metadata fields omit a license, and nvidia-nvtx has conflicting metadata. Exact wheel license members were then read through bounded HTTP ranges, without downloading/executing the full binaries. CUDA runtime and NVSHMEM carry NVIDIA CUDA agreements, cuDNN carries an NVIDIA SDK agreement/supplement, NCCL has a BSD-3-Clause main notice plus an NVTX component reference, and NVTX has Apache-2.0 with the LLVM exception. The inspected cuDNN supplement limits application development to systems with NVIDIA GPUs. These exact terms remain separate; no blanket approval of future binary redistribution is made. The metadata-only cuda-toolkit wheel contains no license member, so its own licensing declaration remains unverified. See [wheel-rights-review.json](../reports/stage7b2/wheel-rights-review.json) for exact wheel URLs and per-notice hashes. NVIDIA also publishes separate [CUDA terms](https://docs.nvidia.com/cuda/archive/13.0.0/eula/index.html) and [cuDNN terms](https://docs.nvidia.com/deeplearning/cudnn/backend/latest/reference/eula.html). No inference of a right to relicense these binaries under MIT is made. The exact affected names and declarations are retained in the inventory.

The MiniLM card declares Apache-2.0, but its standalone LICENSE URL returned 404. These are explicit questions for any future bundled binary/model distribution. The materials are clearly separated installation references here, so they do not prevent applying the approved MIT notice to the current first-party source-only package. No unseparated third-party material with missing rights was identified. Future inclusion of dependencies, weights, external datasets or assets requires a fresh rights review. No permission for such a bundle is claimed.

Original Stage 1-7B.1 reports and notices remain unchanged, including dated statements that no project license had yet been selected. Current licensing is established by this document and LICENSE. See [STAGE7B_PRECOMMIT_REPORT.md](STAGE7B_PRECOMMIT_REPORT.md) for final checks and remaining security/publication conditions.
"""
    )
    if (OUT / "verification-tools.json").exists():
        text += "\n## Referenced verification tools\n\nThese tools and the interpreter are installed separately; no executable or dependency code from them is redistributed here. Their terms remain separate.\n\n| Tool/version used | Verified licensing source | Terms | Action |\n|---|---|---|---|\n"
        for tool in read("verification-tools.json"):
            label = tool["version_output"].splitlines()[0]
            source = tool.get("license_source", tool["source"])
            text += f"| {tool['name']}: {label} | [upstream]({source}) | {tool['license']} | Preserve exact upstream notices before copying any tool code/binary |\n"
    (RELEASE / "docs/THIRD_PARTY_LICENSES.md").write_text(text, encoding="utf-8")


def main():
    rights = inventory()
    if rights["included_rights_blockers"]:
        raise ValueError("Cannot separate affected material; stop before adding the license")
    document(rights)
    official = read("mit-official-text.json")
    copyright_line = "Copyright (c) 2026 Devendra Tapare"
    license_text = (
        "MIT License\n\n"
        + copyright_line
        + "\n\n"
        + "\n\n".join(
            textwrap.fill(p, width=78, break_long_words=False, break_on_hyphens=False)
            for p in official["paragraphs"]
        )
        + "\n"
    )
    path = RELEASE / "LICENSE"
    if path.exists():
        raise ValueError("LICENSE already exists; inspect before modifying")
    path.write_text(license_text, encoding="utf-8", newline="\n")
    decoded = path.read_bytes().decode("utf-8")
    if decoded.splitlines()[2] != copyright_line or decoded.count(copyright_line) != 1:
        raise ValueError("Copyright mismatch")
    paragraphs = re.split(r"\n\s*\n", decoded.strip())[2:]
    if [" ".join(p.split()) for p in paragraphs] != official["paragraphs"]:
        raise ValueError("Official MIT permission/warranty language mismatch")
    save(
        "license-verification.json",
        {
            "license": "MIT",
            "copyright": copyright_line,
            "source": official["source"],
            "complete_permission_and_warranty": True,
            "utf8": True,
            "sha256": digest(path),
            "included_rights_blockers": [],
            "future_external_binary_questions": rights["future_binary_questions"],
        },
    )
    p = RELEASE / "README.md"
    s = p.read_text(encoding="utf-8").replace(
        "Stage 7B.1 security refresh", "Stage 7B.2 licensed verification"
    )
    s = s.replace(
        "No project license has been selected.",
        "The approved project license is MIT; see the License section below.",
    )
    s += (
        "\n## License\n\n[MIT License](LICENSE). Copyright (c) 2026 Devendra Tapare. "
        "This applies only to first-party code and original material the owner owns or may license. "
        "Third-party dependencies, datasets, models and assets retain their own terms; see "
        "[THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md). "
        "No dependency binaries or model weights are bundled.\n"
    )
    p.write_text(s, encoding="utf-8")
    p = RELEASE / "docs/THIRD_PARTY_NOTICES.md"
    s = p.read_text(encoding="utf-8")
    p.write_text(
        "# Current license notice\n\nStage 7B.2 adds the owner-approved MIT license "
        "for authorized first-party material, Copyright (c) 2026 Devendra Tapare. "
        "Third-party terms remain separate. The current inventory is "
        "[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). The dated review below "
        "is preserved as historical context.\n\n" + s,
        encoding="utf-8",
    )
    update_publication()
    print(
        json.dumps(
            {
                "license_added": True,
                "packages_reviewed": 79,
                "included_rights_blockers": [],
                "external_binary_questions": rights["future_binary_questions"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
