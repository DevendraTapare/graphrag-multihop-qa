import json
from pathlib import Path

from pydantic import Field

from app.extraction.chunking import sentences
from app.extraction.models import (
    Contract,
    EntityCandidate,
    IngestionFailure,
    SourceDocument,
    text_hash,
)
from app.graph.fixtures import ROOT
from app.graph.schema import Label
from app.models.fixtures import Entity, normalize_name


class RegistryEntry(Contract):
    entity: Entity
    aliases: list[str] = Field(min_length=1)
    organization_ids: list[str] = Field(default_factory=list)
    project_ids: list[str] = Field(default_factory=list)


class RegistryData(Contract):
    version: str
    entries: list[RegistryEntry]


class EntityRegistry:
    def __init__(self, path: Path | None = None):
        raw = (path or ROOT / "data/extraction/entity_registry.json").read_text(encoding="utf-8")
        self.data = RegistryData.model_validate_json(raw)
        self.version = text_hash(json.dumps(self.data.model_dump(mode="json"), sort_keys=True))
        self.entries = {e.entity.id: e for e in self.data.entries}
        if len(self.entries) != len(self.data.entries):
            raise IngestionFailure("duplicate_registry_identity")
        self.aliases: dict[tuple[Label, str], list[RegistryEntry]] = {}
        for entry in self.data.entries:
            for alias in set(entry.aliases):
                key = (entry.entity.label, normalize_name(alias))
                if not key[1]:
                    raise IngestionFailure("empty_registry_alias")
                if entry not in self.aliases.setdefault(key, []):
                    self.aliases[key].append(entry)

    def surfaces(self, label: Label) -> list[str]:
        return sorted(
            {a for e in self.data.entries if e.entity.label == label for a in e.aliases},
            key=lambda a: (-len(a), a),
        )

    def candidates(self, label: Label, mention: str) -> list[RegistryEntry]:
        return self.aliases.get((label, normalize_name(mention)), [])

    def resolve(
        self, candidate: EntityCandidate, document: SourceDocument, mentions: list[EntityCandidate]
    ) -> str:
        options = self.candidates(candidate.label, candidate.mention)
        if not options:
            raise IngestionFailure("unknown_identity")
        if len(options) == 1:
            return options[0].entity.id
        sentence = next(
            (
                s
                for s in sentences(document.text)
                if s.start <= candidate.start < candidate.end <= s.end
            ),
            None,
        )
        local = [
            m for m in mentions if sentence and sentence.start <= m.start < m.end <= sentence.end
        ]

        def unambiguous_context(items, label):
            result = set()
            for mention in items:
                if mention.label == label:
                    choices = self.candidates(label, mention.mention)
                    if len(choices) == 1:
                        result.add(choices[0].entity.id)
            return result

        projects = unambiguous_context(local, Label.PROJECT)
        orgs = unambiguous_context(local, Label.ORGANIZATION)
        # Deployment shorthand can use one unambiguous project in the original document.
        # People require context in the same statement, never inferred employment from a path.
        if candidate.label == Label.TECHNOLOGY and not projects:
            document_projects = unambiguous_context(mentions, Label.PROJECT)
            if len(document_projects) == 1:
                projects = document_projects
        if projects:
            options = [e for e in options if projects.intersection(e.project_ids)]
        if orgs:
            options = [e for e in options if orgs.intersection(e.organization_ids)]
        if len(options) != 1:
            raise IngestionFailure("ambiguous_identity")
        return options[0].entity.id
