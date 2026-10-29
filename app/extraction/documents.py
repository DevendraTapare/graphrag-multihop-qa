from pathlib import Path, PureWindowsPath

from app.extraction.models import IngestionFailure, SourceDocument, stable_id, text_hash
from app.graph.fixtures import ROOT, read_fixture


def snapshot(source_key: str, filename: str, text: str, original_id=None) -> SourceDocument:
    source_id = stable_id("source", source_key)
    digest = text_hash(text)
    return SourceDocument(
        id=stable_id("autodoc", source_id, digest),
        source_id=source_id,
        source_filename=filename,
        text=text,
        content_hash=digest,
        original_document_id=original_id,
    )


class LocalDocumentLoader:
    def __init__(self, root: Path | None = None, max_bytes: int = 65536):
        self.root = (root or ROOT / "data/fictional").resolve()
        self.max_bytes = max_bytes

    def validate_filename(self, filename: str) -> Path:
        path = Path(filename)
        if (
            path.anchor
            or PureWindowsPath(filename).anchor
            or PureWindowsPath(filename).drive
            or ":" in filename
            or ".." in path.parts
            or path.suffix.lower() not in {".txt", ".md"}
        ):
            raise IngestionFailure("invalid_local_path")
        return path

    def source_id(self, filename: str) -> str:
        path = self.validate_filename(filename)
        return stable_id("source", f"fictional-local:{path.as_posix()}")

    def load(self, filename: str) -> SourceDocument:
        path = self.validate_filename(filename)
        target = self.root / path
        current = target
        while current != self.root:
            if current.is_symlink() or current.is_junction():
                raise IngestionFailure("linked_source_not_allowed")
            current = current.parent
        resolved = target.resolve()
        if not resolved.is_relative_to(self.root):
            raise IngestionFailure("source_outside_fictional_root")
        try:
            with resolved.open("rb") as handle:
                raw = handle.read(self.max_bytes + 1)
        except OSError as exc:
            raise IngestionFailure("source_missing_or_unreadable") from exc
        if len(raw) > self.max_bytes:
            raise IngestionFailure("source_too_large")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise IngestionFailure("invalid_utf8") from exc
        if "\x00" in text:
            raise IngestionFailure("invalid_text_content")
        relative = path.as_posix()
        # Logical source identity is portable across checkouts; CLI has one fixed fictional root.
        return snapshot(f"fictional-local:{relative}", relative, text)


def fixture_documents() -> list[SourceDocument]:
    return [
        snapshot(f"stage1:{d.id}", f"fixtures/corporate.json#{d.id}", d.text, d.id)
        for d in read_fixture().documents
    ]
