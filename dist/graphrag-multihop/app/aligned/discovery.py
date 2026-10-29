"""Discover a conservative registry from source sentences, never evaluation labels."""

import re
from collections import defaultdict
from dataclasses import dataclass

from app.extraction.chunking import sentences
from app.extraction.models import stable_id
from app.extraction.registry import EntityRegistry, RegistryData, RegistryEntry
from app.extraction.rules import NON_ASSERTED
from app.graph.schema import Label as L
from app.models.fixtures import Entity, normalize_name

VERSION = "source-discovery-v1"
NAME = r"[A-Z][A-Za-z0-9-]*(?: (?:[A-Z][A-Za-z0-9-]*|s[0-9]+)){0,7}"
PERSON = NAME + r"(?: \([A-Z][A-Za-z0-9-]* employee [0-9]+\))?"
SPECS = (
    ("management", rf"(?P<person>{PERSON}) (?:manages|leads) Project (?P<project>{NAME})"),
    ("management", rf"Project (?P<project>{NAME}) is managed by (?P<person>{PERSON})"),
    ("employment", rf"(?P<person>{PERSON}) (?:works for|is employed by) (?P<org>{NAME})"),
    ("ownership", rf"Project (?P<project>{NAME}) (?:belongs to|is owned by) (?P<org>{NAME})"),
    (
        "usage",
        rf"Project (?P<project>{NAME}) (?:uses|utilizes) (?:its own |its |a |the )?"
        rf"(?P<technology>{NAME})(?: database)? instance",
    ),
    (
        "hosting",
        rf"The (?P<technology>{NAME}) instance for Project (?P<project>{NAME}) "
        rf"(?:is hosted on|runs on) (?P<platform>{NAME})",
    ),
)
LABELS = {
    "person": L.PERSON,
    "org": L.ORGANIZATION,
    "project": L.PROJECT,
    "technology": L.TECHNOLOGY,
    "platform": L.PLATFORM,
}


@dataclass
class Discovery:
    registry: RegistryData
    mentions: list[dict]
    rejections: list[dict]
    new_ids: list[str]
    reused_ids: list[str]


def discover(documents, base=None):
    base = base or EntityRegistry()
    records, mentions, rejected = [], [], []
    for doc in sorted(documents, key=lambda d: d.id):
        for sentence in sentences(doc.text):
            if sentence.in_code or NON_ASSERTED.search(sentence.text):
                continue
            for rule, expression in SPECS:
                match = re.fullmatch(expression + r"[.!?]?", sentence.text)
                if not match:
                    continue
                record = {"rule": rule, "fields": match.groupdict(), "document_id": doc.id}
                records.append(record)
                for field, surface in match.groupdict().items():
                    start, end = match.span(field)
                    mentions.append(
                        {
                            "document_id": doc.id,
                            "source_id": doc.source_id,
                            "content_hash": doc.content_hash,
                            "start": sentence.start + start,
                            "end": sentence.start + end,
                            "mention": surface,
                            "type": LABELS[field].value,
                            "rule": rule,
                            "project_context": match.groupdict().get("project"),
                        }
                    )
                break
    entries = {e.entity.id: e for e in base.data.entries}
    new, reused = set(), set()

    def candidates(label, surface):
        return [
            e
            for e in entries.values()
            if e.entity.label == label
            and any(normalize_name(a) == normalize_name(surface) for a in e.aliases)
        ]

    def add(label, surface, scope, orgs=(), projects=(), extra=()):
        identifier = stable_id("discovered", label, normalize_name(surface), scope)
        aliases = {surface, *extra}
        if label == L.PROJECT:
            aliases.add("Project " + surface)
        if label == L.PERSON and " (" in surface:
            aliases.add(surface.split(" (")[0])
        entry = RegistryEntry(
            entity=Entity(id=identifier, label=label, name=surface, scope=scope),
            aliases=sorted(aliases),
            organization_ids=sorted(orgs),
            project_ids=sorted(projects),
        )
        previous = entries.get(identifier)
        if previous and previous != entry:
            raise ValueError("Non-deterministic discovery identity")
        entries[identifier] = entry
        new.add(identifier)
        return entry

    surfaces = defaultdict(set)
    for mention in mentions:
        surfaces[L(mention["type"])].add(mention["mention"])
    for label in (L.ORGANIZATION, L.PLATFORM):
        for surface in sorted(surfaces[label]):
            options = candidates(label, surface)
            if options:
                reused.update(e.entity.id for e in options)
            else:
                add(label, surface, "stage5:" + label.value.lower())

    def org_ids(surface):
        return {e.entity.id for e in candidates(L.ORGANIZATION, surface)}

    owners = defaultdict(set)
    employers = defaultdict(set)
    managed = defaultdict(set)
    for record in records:
        f = record["fields"]
        if record["rule"] == "ownership":
            owners[f["project"]].update(org_ids(f["org"]))
        if record["rule"] == "employment":
            employers[f["person"]].update(org_ids(f["org"]))
        if record["rule"] == "management":
            managed[f["person"]].add(f["project"])
    for surface in sorted(surfaces[L.PROJECT]):
        options = candidates(L.PROJECT, surface)
        if options:
            reused.update(e.entity.id for e in options)
            continue
        for owner in sorted(owners[surface]) or [None]:
            add(
                L.PROJECT,
                surface,
                "owner:" + owner if owner else "stage5:project",
                orgs=[owner] if owner else [],
            )
    for surface in sorted(surfaces[L.PERSON]):
        options = candidates(L.PERSON, surface)
        if options:
            reused.update(e.entity.id for e in options)
            continue
        if len(surface.split()) < 2:
            rejected.append(
                {"mention": surface, "type": L.PERSON.value, "reason": "unqualified_new_mononym"}
            )
            continue
        projects = {e.entity.id for p in managed[surface] for e in candidates(L.PROJECT, p)}
        if " (" in surface:
            add(
                L.PERSON,
                surface,
                "employee:" + surface.split(" (")[1].rstrip(")"),
                orgs=employers[surface],
                projects=projects,
            )
            continue
        for employer in sorted(employers[surface]) or [None]:
            scope = "employer:" + employer if employer else "stage5:full-person-name"
            add(L.PERSON, surface, scope, orgs=[employer] if employer else [], projects=projects)
    deployments = defaultdict(set)
    for record in records:
        if "technology" not in record["fields"]:
            continue
        surface, project = record["fields"]["technology"], record["fields"]["project"]
        products = {e.entity.name for e in base.candidates(L.TECHNOLOGY, surface)}
        product = next(iter(products)) if len(products) == 1 else surface
        aliases = {
            a for e in base.candidates(L.TECHNOLOGY, surface) for a in e.aliases if "(" not in a
        }
        deployments[(product, project)].update({surface, *aliases})
    for (surface, project), aliases in sorted(deployments.items()):
        for p in candidates(L.PROJECT, project):
            options = [e for e in candidates(L.TECHNOLOGY, surface) if p.entity.id in e.project_ids]
            if options:
                reused.update(e.entity.id for e in options)
                continue
            add(
                L.TECHNOLOGY,
                surface,
                "deployment:" + p.entity.id,
                projects=[p.entity.id],
                extra=[*aliases, f"{surface} ({project} instance)"],
            )
    # The same normalized full name with several source-backed scopes remains ambiguous.
    return Discovery(
        RegistryData(version=VERSION, entries=sorted(entries.values(), key=lambda e: e.entity.id)),
        mentions,
        rejected,
        sorted(new),
        sorted(reused),
    )
