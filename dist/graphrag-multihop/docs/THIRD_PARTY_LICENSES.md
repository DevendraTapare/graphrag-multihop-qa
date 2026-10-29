# Third-party licenses and rights inventory

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
| [annotated-doc](https://pypi.org/pypi/annotated-doc/0.0.5/json) | 0.0.5 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [annotated-types](https://pypi.org/pypi/annotated-types/0.8.0/json) | 0.8.0 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [anyio](https://pypi.org/pypi/anyio/4.15.1/json) | 4.15.1 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [certifi](https://pypi.org/pypi/certifi/2026.10.23/json) | 2026.10.23 | MPL-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [click](https://pypi.org/pypi/click/8.5.0/json) | 8.5.0 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [cloudpickle](https://pypi.org/pypi/cloudpickle/3.1.2/json) | 3.1.2 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [colorama](https://pypi.org/pypi/colorama/0.4.6/json) | 0.4.6 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [cuda-bindings](https://pypi.org/pypi/cuda-bindings/13.4.4/json) | 13.4.4 | Apache-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [cuda-pathfinder](https://pypi.org/pypi/cuda-pathfinder/1.8.4/json) | 1.8.4 | Apache-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [cuda-toolkit](https://pypi.org/pypi/cuda-toolkit/13.0.3.0/json) | 13.0.3.0 | Not declared in reviewed package metadata; exact wheel terms unverified | External installation reference | Verify exact wheel terms before bundling |
| [defusedxml](https://pypi.org/pypi/defusedxml/0.7.1/json) | 0.7.1 | PSF license version 2 (metadata uses PSFL) | External installation reference | Retain exact upstream license/component notices before bundling |
| [fastapi](https://pypi.org/pypi/fastapi/0.162.0/json) | 0.162.0 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [filelock](https://pypi.org/pypi/filelock/4.2.4/json) | 4.2.4 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [fsspec](https://pypi.org/pypi/fsspec/2026.9.0/json) | 2026.9.0 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [h11](https://pypi.org/pypi/h11/0.16.0/json) | 0.16.0 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [hf-xet](https://pypi.org/pypi/hf-xet/1.7.1/json) | 1.7.1 | Apache-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [httpcore](https://pypi.org/pypi/httpcore/1.0.9/json) | 1.0.9 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [httpx](https://pypi.org/pypi/httpx/0.28.1/json) | 0.28.1 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [huggingface-hub](https://pypi.org/pypi/huggingface-hub/1.33.0/json) | 1.33.0 | Apache-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [idna](https://pypi.org/pypi/idna/3.20/json) | 3.20 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [iniconfig](https://pypi.org/pypi/iniconfig/2.3.1/json) | 2.3.1 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [jinja2](https://pypi.org/pypi/jinja2/3.1.6/json) | 3.1.6 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [joblib](https://pypi.org/pypi/joblib/1.6.0/json) | 1.6.0 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [markdown-it-py](https://pypi.org/pypi/markdown-it-py/4.2.0/json) | 4.2.0 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [markupsafe](https://pypi.org/pypi/markupsafe/3.0.4/json) | 3.0.4 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [mdurl](https://pypi.org/pypi/mdurl/0.1.2/json) | 0.1.2 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [mpmath](https://pypi.org/pypi/mpmath/1.3.0/json) | 1.3.0 | BSD | External installation reference | Retain exact upstream license/component notices before bundling |
| [narwhals](https://pypi.org/pypi/narwhals/2.28.0/json) | 2.28.0 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [neo4j](https://pypi.org/pypi/neo4j/6.4.1/json) | 6.4.1 | Apache-2.0 AND Python-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [networkx](https://pypi.org/pypi/networkx/3.7/json) | 3.7 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [numpy](https://pypi.org/pypi/numpy/2.5.4/json) | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cublas](https://pypi.org/pypi/nvidia-cublas/13.1.1.3/json) | 13.1.1.3 | LicenseRef-NVIDIA-Proprietary | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cuda-cupti](https://pypi.org/pypi/nvidia-cuda-cupti/13.0.85/json) | 13.0.85 | LicenseRef-NVIDIA-Proprietary | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cuda-nvrtc](https://pypi.org/pypi/nvidia-cuda-nvrtc/13.0.88/json) | 13.0.88 | LicenseRef-NVIDIA-Proprietary | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cuda-runtime](https://pypi.org/pypi/nvidia-cuda-runtime/13.0.96/json) | 13.0.96 | NVIDIA CUDA Software License Agreement and supplement (inspected wheel) | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cudnn-cu13](https://pypi.org/pypi/nvidia-cudnn-cu13/9.24.0.43/json) | 9.24.0.43 | NVIDIA SDK License Agreement and cuDNN supplement (inspected wheel) | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cufft](https://pypi.org/pypi/nvidia-cufft/12.0.0.61/json) | 12.0.0.61 | LicenseRef-NVIDIA-Proprietary | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cufile](https://pypi.org/pypi/nvidia-cufile/1.15.1.6/json) | 1.15.1.6 | LicenseRef-NVIDIA-Proprietary | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-curand](https://pypi.org/pypi/nvidia-curand/10.4.0.35/json) | 10.4.0.35 | LicenseRef-NVIDIA-Proprietary | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cusolver](https://pypi.org/pypi/nvidia-cusolver/12.0.4.66/json) | 12.0.4.66 | LicenseRef-NVIDIA-Proprietary | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cusparse](https://pypi.org/pypi/nvidia-cusparse/12.6.3.3/json) | 12.6.3.3 | LicenseRef-NVIDIA-Proprietary | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-cusparselt-cu13](https://pypi.org/pypi/nvidia-cusparselt-cu13/0.8.1/json) | 0.8.1 | NVIDIA Proprietary Software | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-nccl-cu13](https://pypi.org/pypi/nvidia-nccl-cu13/2.30.7/json) | 2.30.7 | BSD-3-Clause main notice; additional NVTX component reference | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-nvjitlink](https://pypi.org/pypi/nvidia-nvjitlink/13.4.92/json) | 13.4.92 | LicenseRef-NVIDIA-Proprietary | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-nvshmem-cu13](https://pypi.org/pypi/nvidia-nvshmem-cu13/3.4.5/json) | 3.4.5 | NVIDIA CUDA Software License Agreement and supplement (inspected wheel) | External installation reference | Retain exact upstream license/component notices before bundling |
| [nvidia-nvtx](https://pypi.org/pypi/nvidia-nvtx/13.0.85/json) | 13.0.85 | Apache-2.0 WITH LLVM-exception (inspected wheel; metadata classifier conflicts) | External installation reference | Retain exact upstream license/component notices before bundling |
| [opentelemetry-api](https://pypi.org/pypi/opentelemetry-api/1.45.1/json) | 1.45.1 | Apache-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [packaging](https://pypi.org/pypi/packaging/26.3/json) | 26.3 | Apache-2.0 OR BSD-2-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [pluggy](https://pypi.org/pypi/pluggy/1.7.0/json) | 1.7.0 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [psutil](https://pypi.org/pypi/psutil/7.2.2/json) | 7.2.2 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [pydantic](https://pypi.org/pypi/pydantic/2.14.1/json) | 2.14.1 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [pydantic-core](https://pypi.org/pypi/pydantic-core/2.50.1/json) | 2.50.1 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [pydantic-settings](https://pypi.org/pypi/pydantic-settings/2.16.1/json) | 2.16.1 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [pygments](https://pypi.org/pypi/pygments/2.21.0/json) | 2.21.0 | BSD-2-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [pytest](https://pypi.org/pypi/pytest/9.2.0/json) | 9.2.0 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [python-dotenv](https://pypi.org/pypi/python-dotenv/1.2.4/json) | 1.2.4 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [pytz](https://pypi.org/pypi/pytz/2026.5/json) | 2026.5 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [pyyaml](https://pypi.org/pypi/pyyaml/6.0.3/json) | 6.0.3 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [regex](https://pypi.org/pypi/regex/2026.9.29/json) | 2026.9.29 | Apache-2.0 AND CNRI-Python | External installation reference | Retain exact upstream license/component notices before bundling |
| [rich](https://pypi.org/pypi/rich/15.0.0/json) | 15.0.0 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [ruff](https://pypi.org/pypi/ruff/0.17.3/json) | 0.17.3 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [safetensors](https://pypi.org/pypi/safetensors/0.8.0/json) | 0.8.0 | Apache-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [scikit-learn](https://pypi.org/pypi/scikit-learn/1.9.1/json) | 1.9.1 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [scipy](https://pypi.org/pypi/scipy/1.18.1/json) | 1.18.1 | BSD-3-Clause (project; bundled components retain separate notices) | External installation reference | Retain exact upstream license/component notices before bundling |
| [sentence-transformers](https://pypi.org/pypi/sentence-transformers/5.7.0/json) | 5.7.0 | Apache-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [setuptools](https://pypi.org/pypi/setuptools/84.2.1/json) | 84.2.1 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [shellingham](https://pypi.org/pypi/shellingham/1.5.4/json) | 1.5.4 | ISC License | External installation reference | Retain exact upstream license/component notices before bundling |
| [starlette](https://pypi.org/pypi/starlette/1.10.0/json) | 1.10.0 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [sympy](https://pypi.org/pypi/sympy/1.14.0/json) | 1.14.0 | BSD | External installation reference | Retain exact upstream license/component notices before bundling |
| [threadpoolctl](https://pypi.org/pypi/threadpoolctl/3.7.0/json) | 3.7.0 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |
| [tokenizers](https://pypi.org/pypi/tokenizers/0.23.3/json) | 0.23.3 | Apache-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [torch](https://pypi.org/pypi/torch/2.14.1/json) | 2.14.1 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [tqdm](https://pypi.org/pypi/tqdm/4.70.1/json) | 4.70.1 | MPL-2.0 AND MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [transformers](https://pypi.org/pypi/transformers/5.17.0/json) | 5.17.0 | Apache 2.0 License | External installation reference | Retain exact upstream license/component notices before bundling |
| [triton](https://pypi.org/pypi/triton/3.8.0/json) | 3.8.0 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [typer](https://pypi.org/pypi/typer/0.27.3/json) | 0.27.3 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [typing-extensions](https://pypi.org/pypi/typing-extensions/4.16.0/json) | 4.16.0 | PSF-2.0 | External installation reference | Retain exact upstream license/component notices before bundling |
| [typing-inspection](https://pypi.org/pypi/typing-inspection/0.4.4/json) | 0.4.4 | MIT | External installation reference | Retain exact upstream license/component notices before bundling |
| [uvicorn](https://pypi.org/pypi/uvicorn/0.54.0/json) | 0.54.0 | BSD-3-Clause | External installation reference | Retain exact upstream license/component notices before bundling |

## Notice requirements and unresolved questions

If third-party code or binaries are redistributed later, retain their exact copyright, license and component notices. MIT requires its notice; BSD/ISC variants retain their stated notices/conditions. [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) includes license, modification and applicable NOTICE requirements and does not grant trademark rights. [MPL-2.0](https://www.mozilla.org/en-US/MPL/2.0/) keeps covered-source obligations for its covered portions. PSF/Python and combined-license packages require their exact agreements, not an assumed blanket MIT substitute. These are review pointers; the referenced licenses control.

Several CUDA package metadata fields omit a license, and nvidia-nvtx has conflicting metadata. Exact wheel license members were then read through bounded HTTP ranges, without downloading/executing the full binaries. CUDA runtime and NVSHMEM carry NVIDIA CUDA agreements, cuDNN carries an NVIDIA SDK agreement/supplement, NCCL has a BSD-3-Clause main notice plus an NVTX component reference, and NVTX has Apache-2.0 with the LLVM exception. The inspected cuDNN supplement limits application development to systems with NVIDIA GPUs. These exact terms remain separate; no blanket approval of future binary redistribution is made. The metadata-only cuda-toolkit wheel contains no license member, so its own licensing declaration remains unverified. See [wheel-rights-review.json](../reports/stage7b2/wheel-rights-review.json) for exact wheel URLs and per-notice hashes. NVIDIA also publishes separate [CUDA terms](https://docs.nvidia.com/cuda/archive/13.0.0/eula/index.html) and [cuDNN terms](https://docs.nvidia.com/deeplearning/cudnn/backend/latest/reference/eula.html). No inference of a right to relicense these binaries under MIT is made. The exact affected names and declarations are retained in the inventory.

The MiniLM card declares Apache-2.0, but its standalone LICENSE URL returned 404. These are explicit questions for any future bundled binary/model distribution. The materials are clearly separated installation references here, so they do not prevent applying the approved MIT notice to the current first-party source-only package. No unseparated third-party material with missing rights was identified. Future inclusion of dependencies, weights, external datasets or assets requires a fresh rights review. No permission for such a bundle is claimed.

Original Stage 1-7B.1 reports and notices remain unchanged, including dated statements that no project license had yet been selected. Current licensing is established by this document and LICENSE. See [STAGE7B_PRECOMMIT_REPORT.md](STAGE7B_PRECOMMIT_REPORT.md) for final checks and remaining security/publication conditions.

## Referenced verification tools

These tools and the interpreter are installed separately; no executable or dependency code from them is redistributed here. Their terms remain separate.

| Tool/version used | Verified licensing source | Terms | Action |
|---|---|---|---|
| pip-audit: pip-audit 2.10.1 | [upstream](https://github.com/pypa/pip-audit/blob/v2.10.1/LICENSE) | Apache-2.0 | Preserve exact upstream notices before copying any tool code/binary |
| bandit: bandit 1.9.4 | [upstream](https://pypi.org/pypi/bandit/1.9.4/json) | Apache-2.0 | Preserve exact upstream notices before copying any tool code/binary |
| gitleaks: 8.30.1 | [upstream](https://github.com/gitleaks/gitleaks/blob/v8.30.1/LICENSE) | MIT | Preserve exact upstream notices before copying any tool code/binary |
| python: Python 3.12.13 | [upstream](https://github.com/python/cpython/blob/v3.12.13/LICENSE) | PSF license and listed component notices | Preserve exact upstream notices before copying any tool code/binary |
