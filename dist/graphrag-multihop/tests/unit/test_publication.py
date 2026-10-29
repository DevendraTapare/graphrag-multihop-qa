"""Publication safety and source preservation, in addition to all research regressions."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts import portfolio


def test_demo_refuses_a_nonpublication_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(portfolio, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="clean publication"):
        portfolio.require_publication()


@pytest.mark.parametrize(
    ("environment", "uri"),
    [
        ("production", "bolt://127.0.0.1:37690"),
        ("development", "bolt://example.invalid:7687"),
        ("development", "neo4j+s://example.invalid:7687"),
    ],
)
def test_demo_refuses_remote_or_nondevelopment_database(tmp_path, monkeypatch, environment, uri):
    (tmp_path / "PUBLICATION.json").write_text("{}")
    monkeypatch.setattr(portfolio, "ROOT", tmp_path)
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setenv("NEO4J_URI", uri)
    monkeypatch.setenv("NEO4J_PASSWORD", "unit-test-secret-12345")
    with pytest.raises(ValueError, match="development database on loopback"):
        portfolio.require_publication()


def test_publication_preserves_every_core_source_and_dataset():
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "PUBLICATION.json").read_text())
    assert manifest["core_source_hashes"]
    for relative, expected in manifest["core_source_hashes"].items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, relative


def test_demo_accepts_explicit_local_development_publication(tmp_path, monkeypatch):
    (tmp_path / "PUBLICATION.json").write_text("{}")
    monkeypatch.setattr(portfolio, "ROOT", tmp_path)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("NEO4J_URI", "bolt://127.0.0.1:37690")
    monkeypatch.setenv("NEO4J_PASSWORD", "unit-test-secret-12345")
    assert portfolio.require_publication().neo4j_uri == "bolt://127.0.0.1:37690"
    for port in (7687, 17688, 27689):
        monkeypatch.setenv("NEO4J_URI", f"bolt://127.0.0.1:{port}")
        with pytest.raises(ValueError, match="historical research port"):
            portfolio.require_publication()
