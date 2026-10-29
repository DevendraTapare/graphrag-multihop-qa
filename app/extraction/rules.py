import re
from typing import Protocol

from app.extraction.chunking import Sentence, covering_chunk, sentences
from app.extraction.models import (
    CandidateBatch,
    EntityCandidate,
    Rejection,
    RelationCandidate,
    SourceDocument,
    TextChunk,
    stable_id,
    text_hash,
)
from app.extraction.registry import EntityRegistry
from app.graph.schema import FactType, Label


class Extractor(Protocol):
    version: str

    def extract_entities(
        self, document: SourceDocument, chunks: list[TextChunk]
    ) -> list[EntityCandidate]: ...

    def extract_relations(
        self, document: SourceDocument, chunks: list[TextChunk], entities: list[EntityCandidate]
    ) -> CandidateBatch: ...


NON_ASSERTED = re.compile(
    r"\b(?:not|never|no longer|doesn't|isn't|may|might|could|would|allegedly|reportedly|"
    r"rumou?r|if|denies|suppose|example)\b|^[\"'\u201c\u2018>]"
    r"|^(?:system|assistant|user|ignore|instruction)\s*[: ]",
    re.IGNORECASE,
)


class DeterministicExtractor:
    def __init__(self, registry: EntityRegistry):
        self.registry = registry

        def aliases(label):
            return "(?:" + "|".join(re.escape(a) for a in registry.surfaces(label)) + ")"

        person, org, project, technology, platform = [aliases(label) for label in Label]
        definitions = [
            (
                "manages-active",
                FactType.MANAGES,
                rf"(?P<s>{person}) (?:manages|leads) (?P<o>{project})(?: at {org})?",
            ),
            (
                "manages-passive",
                FactType.MANAGES,
                rf"(?P<o>{project}) is managed by (?P<s>{person})",
            ),
            (
                "employment",
                FactType.WORKS_FOR,
                rf"(?P<s>{person}) (?:works for|is employed by) (?P<o>{org})",
            ),
            (
                "uses",
                FactType.USES,
                rf"(?P<s>{project}) (?:uses|utilizes) (?:(?:its own|its|an?|the) )?"
                rf"(?P<o>{technology})(?: (?:database )?instance)?",
            ),
            (
                "hosting",
                FactType.HOSTED_ON,
                rf"(?:The )?(?P<s>{technology})(?: (?:database )?instance)?"
                rf"(?: for {project})? (?:is hosted on|runs on) (?P<o>{platform})",
            ),
            (
                "ownership",
                FactType.BELONGS_TO,
                rf"(?P<s>{project}) (?:belongs to|is owned by) (?P<o>{org})",
            ),
        ]
        self.patterns = [
            (id, predicate, re.compile(pattern + r"[.!?]?", re.IGNORECASE))
            for id, predicate, pattern in definitions
        ]
        self.version = "rules-v3:" + text_hash(str(definitions))[:24]
        self.mention_patterns = [
            (
                label,
                re.compile(
                    r"(?<!\w)(?:"
                    + "|".join(re.escape(a) for a in registry.surfaces(label))
                    + r")(?!\w)",
                    re.IGNORECASE,
                ),
            )
            for label in Label
        ]

    def approved_match(self, sentence: Sentence):
        if sentence.in_code or NON_ASSERTED.search(sentence.text):
            return None
        return next(
            (
                (id, predicate, m)
                for id, predicate, pattern in self.patterns
                if (m := pattern.fullmatch(sentence.text))
            ),
            None,
        )

    def extract_entities(
        self, document: SourceDocument, chunks: list[TextChunk]
    ) -> list[EntityCandidate]:
        matches = []
        for label, pattern in self.mention_patterns:
            matches.extend(
                (m.start(), m.end(), label, m.group()) for m in pattern.finditer(document.text)
            )
        # A registered first name or project prefix must not swallow an unknown longer identity.
        boundary_words = {
            "manages",
            "leads",
            "is",
            "works",
            "uses",
            "utilizes",
            "belongs",
            "runs",
            "does",
            "might",
            "may",
            "and",
            "at",
            "for",
            "oversees",
        }
        for start, end, label, _ in list(matches):
            if label not in {Label.PERSON, Label.PROJECT, Label.ORGANIZATION}:
                continue
            extended = end
            for word in re.finditer(r" ([A-Z][\w-]*)", document.text[end:]):
                if word.start() != extended - end or word.group(1).casefold() in boundary_words:
                    break
                extended = end + word.end()
            if extended > end:
                matches.append((start, extended, label, document.text[start:extended]))
        # Unknown longer typed names outrank known prefixes, including Project Atlas North.
        for match in re.finditer(
            r"\b(?P<type>Person|Organization|Project|Technology|Platform) "
            r"(?P<name>[A-Z][\w-]*(?: [A-Z][\w-]*){0,2})",
            document.text,
        ):
            matches.append((match.start(), match.end(), Label(match["type"]), match.group()))
        matches.sort(key=lambda m: (m[0], -(m[1] - m[0]), m[2]))
        selected = []
        for start, end, label, mention in matches:
            if any(start < c.end and c.start < end for c in selected):
                continue
            chunk = covering_chunk(chunks, start, end)
            if chunk:
                selected.append(
                    EntityCandidate(
                        id=stable_id("mention", document.id, start, end, label, self.version),
                        mention=mention,
                        label=label,
                        source_document_id=document.id,
                        source_chunk_id=chunk.id,
                        start=start,
                        end=end,
                        extraction_version=self.version,
                    )
                )
        return sorted(selected, key=lambda c: (c.start, c.end, c.label))

    def extract_relations(
        self, document: SourceDocument, chunks: list[TextChunk], entities: list[EntityCandidate]
    ) -> CandidateBatch:
        relations, rejections = [], []
        for sentence in sentences(document.text):
            local = [e for e in entities if sentence.start <= e.start < e.end <= sentence.end]
            if len(local) < 2:
                continue
            chunk = covering_chunk(chunks, sentence.start, sentence.end)
            match = self.approved_match(sentence)
            if not chunk or not match:
                reason = (
                    "sentence_exceeds_chunk"
                    if not chunk
                    else "non_asserted_statement"
                    if sentence.in_code or NON_ASSERTED.search(sentence.text)
                    else "unsupported_pattern"
                )
                rejections.append(
                    Rejection(
                        candidate_id=stable_id(
                            "sentence", document.id, sentence.start, sentence.end
                        ),
                        kind="sentence",
                        reason=reason,
                        source_document_id=document.id,
                        source_chunk_id=chunk.id if chunk else None,
                        start=sentence.start,
                        end=sentence.end,
                        text=sentence.text,
                    )
                )
                continue
            rule_id, predicate, found = match
            endpoints = []
            for group in ("s", "o"):
                start, end = sentence.start + found.start(group), sentence.start + found.end(group)
                endpoint = next((e for e in local if (e.start, e.end) == (start, end)), None)
                if endpoint is None:
                    break
                endpoints.append(endpoint.model_copy(update={"source_chunk_id": chunk.id}))
            if len(endpoints) == 2:
                relations.append(
                    RelationCandidate(
                        id=stable_id(
                            "candidate",
                            document.id,
                            sentence.start,
                            sentence.end,
                            predicate,
                            self.version,
                        ),
                        subject=endpoints[0],
                        object=endpoints[1],
                        predicate=predicate,
                        source_document_id=document.id,
                        source_chunk_id=chunk.id,
                        start=sentence.start,
                        end=sentence.end,
                        evidence=sentence.text,
                        rule_id=rule_id,
                        extraction_version=self.version,
                    )
                )
        return CandidateBatch(entities=entities, relations=relations, rejections=rejections)
