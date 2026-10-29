import json
from pathlib import Path

from app.models.fixtures import Evaluation, Fixture, edge_id, fingerprint, normalize_name

ROOT = Path(__file__).resolve().parents[2]


def read_fixture(path: Path | None = None) -> Fixture:
    return Fixture.model_validate_json((path or ROOT / "data/fixtures/corporate.json").read_text())


def read_evaluations() -> list[Evaluation]:
    return [
        Evaluation.model_validate(e)
        for e in json.loads((ROOT / "data/evaluation/questions.json").read_text())
    ]


def graph_rows(fixture: Fixture) -> tuple[list[dict], list[dict]]:
    nodes = []
    edges = []

    def node(label, properties):
        properties = {**properties, "fixture_id": fixture.id}
        properties["fingerprint"] = fingerprint(properties)
        nodes.append({"label": label, "properties": properties})

    def edge(kind, source, target, properties):
        properties = {"id": edge_id(kind, source, target), **properties, "fixture_id": fixture.id}
        properties["fingerprint"] = fingerprint(
            {
                "kind": kind,
                "source": source,
                "target": target,
                **properties,
            }
        )
        edges.append({"kind": kind, "source": source, "target": target, "properties": properties})

    for e in fixture.entities:
        props = e.model_dump(mode="json", exclude={"label"})
        props["normalized_name"] = normalize_name(e.name)
        node(e.label.value, props)
    for d in fixture.documents:
        node("Document", d.model_dump())
    for c in fixture.chunks:
        node("Chunk", c.model_dump())
        edge("PART_OF", c.id, c.document_id, {})
        edge("DERIVED_FROM", c.id, c.document_id, {"method": "verbatim_excerpt"})
    mentions = set()
    for f in fixture.facts:
        edge(
            f.predicate.value,
            f.subject,
            f.object,
            f.model_dump(mode="json", exclude={"subject", "predicate", "object"}),
        )
        mentions.update((f.source_chunk_id, entity) for entity in (f.subject, f.object))
    for source, target in sorted(mentions):
        edge("MENTIONS", source, target, {})
    return nodes, edges
