import re
from dataclasses import dataclass

from app.extraction.models import ChunkOptions, SourceDocument, TextChunk, stable_id

CHUNKER_VERSION = "sentence-windows-v3"


@dataclass(frozen=True)
class Sentence:
    start: int
    end: int
    text: str
    in_code: bool = False


def sentences(text: str) -> list[Sentence]:
    """Original offsets, with Markdown code blocks kept outside asserted prose."""
    result = []
    position, fenced = 0, False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            position += len(line)
            continue
        content = line.rstrip("\r\n")
        for match in re.finditer(r"[^.!?\r\n]+(?:[.!?]+|$)", content):
            raw = match.group()
            prefix = re.match(r"\s*(?:[-*+]\s+)?", raw).end()
            end = match.end() - (len(raw) - len(raw.rstrip()))
            start = match.start() + prefix
            if start < end:
                result.append(Sentence(position + start, position + end, line[start:end], fenced))
        position += len(line)
    return result


def split_document(
    document: SourceDocument, options: ChunkOptions, version: str
) -> list[TextChunk]:
    text = document.text
    boundaries = [m.end() for m in re.finditer(r"[.!?](?=\s|$)|\r?\n", text)]
    chunks = []
    source_sentences = sentences(text)
    start = 0
    while start < len(text):
        end = min(start + options.size, len(text))
        if end < len(text):
            fitting = [b for b in boundaries if start + options.overlap < b <= end]
            if fitting:
                end = fitting[-1]
        chunks.append(
            TextChunk(
                id=stable_id("autochunk", document.id, version, options.model_dump(), start, end),
                document_id=document.id,
                content_hash=document.content_hash,
                processing_version=version,
                start=start,
                end=end,
                text=text[start:end],
            )
        )
        if end == len(text):
            break
        next_start = max(start + 1, end - options.overlap)
        upcoming = next((s for s in source_sentences if s.start >= end), None)
        if upcoming and upcoming.end - upcoming.start <= options.size:
            # Reduce overlap when necessary to keep the next sentence whole, without source gaps.
            next_start = max(next_start, min(end, upcoming.end - options.size))
        start = next_start
    return chunks


def covering_chunk(chunks: list[TextChunk], start: int, end: int) -> TextChunk | None:
    return next((c for c in chunks if c.start <= start and end <= c.end), None)
