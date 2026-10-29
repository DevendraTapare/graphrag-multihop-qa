"""Author the explicit fictional alias registry; never infer identities at ingestion time."""

import json

from app.extraction.registry import RegistryData, RegistryEntry
from app.graph.fixtures import ROOT, read_fixture
from app.graph.schema import Label
from app.models.fixtures import Entity


def build_registry() -> RegistryData:
    fixture = read_fixture()
    contexts = [
        ("atlas", "lumen", "priya", "postgres-atlas"),
        ("atlas-east", "cedar", "morgan", "postgres-east"),
        ("beacon", "lumen", "sam", "redis"),
        ("comet", "cedar", "lee-north", "neo4j"),
        ("delta", "tidal", "lee-south", "kafka"),
        ("echo", "tidal", "noor", "duckdb"),
    ]
    entries = []
    project_names = {e.id: e.name for e in fixture.entities if e.label == Label.PROJECT}
    for entity in fixture.entities:
        aliases = [entity.name]
        orgs, projects = [], []
        if entity.label == Label.PROJECT:
            aliases.append(f"Project {entity.name}")
        for project, org, person, tech in contexts:
            if entity.id in {f"project:{project}", f"person:{person}", f"tech:{tech}"}:
                orgs.append(f"org:{org}")
                projects.append(f"project:{project}")
        if entity.id == "person:priya":
            aliases.append("Priya (Lumen employee 001)")
        if entity.id == "person:lee-north":
            aliases.extend(["Lee", "Lee Chen (Cedar employee 002)"])
        if entity.id == "person:lee-south":
            aliases.extend(["Lee", "Lee Chen (Tidal employee 001)"])
        if entity.name == "PostgreSQL":
            aliases.extend(["Postgres", f"PostgreSQL ({project_names[projects[0]]} instance)"])
        aliases.extend(
            {
                "platform:aws": ["Amazon Web Services"],
                "platform:azure": ["Microsoft Azure"],
                "platform:gcp": ["Google Cloud"],
            }.get(entity.id, [])
        )
        entries.append(
            RegistryEntry(
                entity=entity, aliases=aliases, organization_ids=orgs, project_ids=projects
            )
        )
    entries.append(
        RegistryEntry(
            entity=Entity(
                id="person:priya-cedar",
                label=Label.PERSON,
                name="Priya",
                scope="cedar_employee_003",
            ),
            aliases=["Priya", "Priya (Cedar employee 003)"],
            organization_ids=["org:cedar"],
            project_ids=["project:atlas-east"],
        )
    )
    return RegistryData(version="fictional-aliases-v1", entries=entries)


def main():
    path = ROOT / "data/extraction/entity_registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_registry().model_dump(mode="json"), indent=2) + "\n", encoding="utf-8"
    )
    print("Wrote controlled fictional registry")


if __name__ == "__main__":
    main()
