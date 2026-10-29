from pathlib import Path

import pytest
from pydantic import ValidationError

from app.extraction.chunking import split_document
from app.extraction.documents import LocalDocumentLoader, fixture_documents, snapshot
from app.extraction.models import ChunkOptions, IngestionFailure, text_hash


@pytest.mark.parametrize("extension", [".txt", ".md", ".TXT"])
def test_local_loader_preserves_utf8_crlf_and_identity(tmp_path, extension):
    content = "Café 🧪\r\nPriya manages Project Atlas.\r\n"
    name = "fictional" + extension
    (tmp_path / name).write_bytes(content.encode("utf-8"))
    loader = LocalDocumentLoader(tmp_path)
    first, second = loader.load(name), loader.load(name)
    assert first.id == second.id and first.source_id == second.source_id
    assert first.text == content and first.content_hash == text_hash(content)
    assert first.source_filename == name
    assert first.created_at.tzinfo is not None


@pytest.mark.parametrize(
    "name",
    [
        "../other.txt",
        "https://example.com/a.txt",
        "C:/private/a.txt",
        "/private/a.txt",
        "a.pdf",
        "a.py",
        "missing.txt",
        "a/../../b.txt",
    ],
)
def test_loader_rejects_invalid_or_missing_sources(tmp_path, name):
    with pytest.raises(IngestionFailure):
        LocalDocumentLoader(tmp_path).load(name)


@pytest.mark.parametrize(
    "raw,category",
    [
        (b"\xff", "invalid_utf8"),
        (b"hello\x00", "invalid_text_content"),
        (b"12345", "source_too_large"),
    ],
)
def test_encoding_content_and_size(tmp_path, raw, category):
    (tmp_path / "sample.txt").write_bytes(raw)
    with pytest.raises(IngestionFailure, match=category):
        LocalDocumentLoader(tmp_path, max_bytes=4 if category == "source_too_large" else 16).load(
            "sample.txt"
        )


def test_size_limit_empty_file_and_link_guard(tmp_path, monkeypatch):
    (tmp_path / "sample.txt").write_bytes(b"1234")
    assert LocalDocumentLoader(tmp_path, max_bytes=4).load("sample.txt").text == "1234"
    (tmp_path / "empty.txt").write_bytes(b"")
    assert LocalDocumentLoader(tmp_path).load("empty.txt").text == ""
    monkeypatch.setattr(Path, "is_symlink", lambda self: self.name == "sample.txt")
    with pytest.raises(IngestionFailure, match="linked_source"):
        LocalDocumentLoader(tmp_path).load("sample.txt")


def test_source_changes_keep_logical_id_and_version_content(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_bytes(b"First fictional version.")
    first = LocalDocumentLoader(tmp_path).load(path.name)
    path.write_bytes(b"Corrected fictional version.")
    second = LocalDocumentLoader(tmp_path).load(path.name)
    assert first.source_id == second.source_id
    assert first.id != second.id and first.content_hash != second.content_hash


@pytest.mark.parametrize("size,overlap", [(0, 0), (100, 100), (100, 101), (100, -1)])
def test_chunk_configuration_validation(size, overlap):
    with pytest.raises(ValidationError):
        ChunkOptions(size=size, overlap=overlap)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "🧪",
        "Line one.\r\nCafé uses nothing.\n",
        "X" * 179,
        "Priya manages Project Atlas. " * 20,
    ],
)
def test_chunks_have_exact_offsets_coverage_and_deterministic_ids(text):
    document = snapshot("test:chunk", "chunk.txt", text)
    options = ChunkOptions(size=70, overlap=12)
    chunks = split_document(document, options, "processing:test")
    assert chunks == split_document(document, options, "processing:test")
    assert len({c.id for c in chunks}) == len(chunks)
    covered = set()
    for c in chunks:
        assert c.text == text[c.start : c.end]
        assert c.document_id == document.id and c.content_hash == document.content_hash
        assert 0 < len(c.text) <= 70
        covered.update(range(c.start, c.end))
    assert covered == set(range(len(text)))


def test_chunker_prefers_sentence_boundaries_and_versions():
    document = snapshot("test:sentences", "sentences.md", "A" * 30 + ". " + "B" * 40 + ".")
    options = ChunkOptions(size=60, overlap=4)
    chunks = split_document(document, options, "version:one")
    assert chunks[0].text.endswith(".")
    assert chunks[0].id != split_document(document, options, "version:two")[0].id


def test_fixture_loading_preserves_original_texts():
    from app.graph.fixtures import read_fixture

    sources = fixture_documents()
    assert len(sources) == 12
    assert [d.text for d in sources] == [d.text for d in read_fixture().documents]
    assert all(d.id != d.original_document_id for d in sources)
