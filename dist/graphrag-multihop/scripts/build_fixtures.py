"""Rebuild checked-in, fictional fixtures without a database or network calls."""

import json

from app.graph.fixtures import ROOT
from app.models.fixtures import Evaluation, Fixture, validate_evaluations


def build() -> tuple[Fixture, list[Evaluation]]:
    entities = []

    def entity(id, label, name, scope):
        entities.append(dict(id=id, label=label, name=name, scope=scope))

    for id, name in [
        ("lumen", "Lumen Orchard"),
        ("cedar", "Cedar Kite"),
        ("tidal", "Tidal Lantern"),
    ]:
        entity(f"org:{id}", "Organization", name, "fictional_registry")
    for id, name, scope in [
        ("priya", "Priya", "lumen_employee_001"),
        ("morgan", "Morgan", "cedar_employee_001"),
        ("sam", "Sam", "lumen_employee_002"),
        ("lee-north", "Lee Chen", "cedar_employee_002"),
        ("lee-south", "Lee Chen", "tidal_employee_001"),
        ("noor", "Noor", "tidal_employee_002"),
        ("ivo", "Ivo", "directory_only_001"),
        ("una", "Una", "directory_only_002"),
    ]:
        entity(f"person:{id}", "Person", name, scope)
    projects = [
        ("atlas", "Atlas", "lumen", "priya", "postgres-atlas", "PostgreSQL", "aws"),
        ("atlas-east", "Atlas East", "cedar", "morgan", "postgres-east", "PostgreSQL", "azure"),
        ("beacon", "Beacon", "lumen", "sam", "redis", "Redis", "gcp"),
        ("comet", "Comet", "cedar", "lee-north", "neo4j", "Neo4j", "azure"),
        ("delta", "Delta", "tidal", "lee-south", "kafka", "Kafka", "aws"),
        ("echo", "Echo", "tidal", "noor", "duckdb", "DuckDB", "gcp"),
    ]
    for project, name, org, _, tech, tech_name, _ in projects:
        entity(f"project:{project}", "Project", name, org)
        entity(f"tech:{tech}", "Technology", tech_name, f"{project}_deployment")
    for id, name in [("aws", "AWS"), ("azure", "Azure"), ("gcp", "GCP")]:
        entity(f"platform:{id}", "Platform", name, "cloud_vendor")

    facts, docs, chunks = [], [], []

    def document(number, title, statements):
        did, cid = f"doc:{number:02}", f"chunk:{number:02}"
        text = " ".join(statement[3] for statement in statements)
        docs.append(dict(id=did, title=title, text=text))
        chunks.append(dict(id=cid, document_id=did, start=0, end=len(text), text=text))
        for subject, predicate, object, quote in statements:
            facts.append(
                dict(
                    id=f"fact:{len(facts) + 1:03}",
                    subject=subject,
                    predicate=predicate,
                    object=object,
                    source_document_id=did,
                    source_chunk_id=cid,
                    quote=quote,
                    extraction_method="manual_fixture",
                    confidence=1.0,
                    created_at="2026-01-01T00:00:00Z",
                )
            )

    names = {e["id"]: e["name"] for e in entities}
    # Atlas facts deliberately span three independent documents.
    document(
        1,
        "Lumen staffing",
        [
            (
                "person:priya",
                "MANAGES",
                "project:atlas",
                "Priya manages Project Atlas at Lumen Orchard.",
            ),
            ("person:priya", "WORKS_FOR", "org:lumen", "Priya works for Lumen Orchard."),
        ],
    )
    document(
        2,
        "Atlas database decision",
        [
            (
                "project:atlas",
                "USES",
                "tech:postgres-atlas",
                "Project Atlas uses its PostgreSQL database instance.",
            ),
            ("project:atlas", "BELONGS_TO", "org:lumen", "Project Atlas belongs to Lumen Orchard."),
        ],
    )
    document(
        3,
        "Atlas hosting inventory",
        [
            (
                "tech:postgres-atlas",
                "HOSTED_ON",
                "platform:aws",
                "The PostgreSQL instance for Project Atlas is hosted on AWS.",
            ),
        ],
    )
    # Atlas East has similar naming, but a distinct database instance and hosting evidence.
    project, name, org, manager, tech, tech_name, platform = projects[1]
    document(
        4,
        "Atlas East inventory",
        [
            (
                "person:morgan",
                "MANAGES",
                "project:atlas-east",
                "Morgan manages Project Atlas East at Cedar Kite.",
            ),
            ("person:morgan", "WORKS_FOR", "org:cedar", "Morgan works for Cedar Kite."),
            (
                "project:atlas-east",
                "BELONGS_TO",
                "org:cedar",
                "Project Atlas East belongs to Cedar Kite.",
            ),
            (
                "project:atlas-east",
                "USES",
                "tech:postgres-east",
                "Project Atlas East uses its own PostgreSQL instance.",
            ),
            (
                "tech:postgres-east",
                "HOSTED_ON",
                "platform:azure",
                "The PostgreSQL instance for Project Atlas East is hosted on Azure.",
            ),
        ],
    )
    for i, (project, name, org, manager, tech, tech_name, platform) in enumerate(projects[2:]):
        person = f"person:{manager}"
        display = names[person]
        qualifier = (
            " (Cedar employee 002)"
            if manager == "lee-north"
            else (" (Tidal employee 001)" if manager == "lee-south" else "")
        )
        document(
            5 + i * 2,
            f"{name} staffing",
            [
                (
                    person,
                    "MANAGES",
                    f"project:{project}",
                    f"{display}{qualifier} manages Project {name}.",
                ),
                (
                    person,
                    "WORKS_FOR",
                    f"org:{org}",
                    f"{display}{qualifier} works for {names[f'org:{org}']}.",
                ),
                (
                    f"project:{project}",
                    "BELONGS_TO",
                    f"org:{org}",
                    f"Project {name} belongs to {names[f'org:{org}']}.",
                ),
            ],
        )
        document(
            6 + i * 2,
            f"{name} technology inventory",
            [
                (
                    f"project:{project}",
                    "USES",
                    f"tech:{tech}",
                    f"Project {name} uses its {tech_name} instance.",
                ),
                (
                    f"tech:{tech}",
                    "HOSTED_ON",
                    f"platform:{platform}",
                    f"The {tech_name} instance for Project {name} is hosted on "
                    f"{names[f'platform:{platform}']}.",
                ),
            ],
        )
    # Directory entries make no employment or management claims about Ivo and Una.
    docs[-1]["text"] += " Directory-only contacts: Ivo and Una; their roles are not recorded."
    chunks[-1].update(text=docs[-1]["text"], end=len(docs[-1]["text"]))
    fixture = Fixture.model_validate(
        dict(
            id="fixture:corporate-v1",
            entities=entities,
            documents=docs,
            chunks=chunks,
            facts=facts,
        )
    )
    evaluations = []

    def evaluation(id, question, fact_ids):
        selected = [next(f for f in fixture.facts if f.id == fid) for fid in fact_ids]
        path = [selected[0].subject, *[f.object for f in selected]]
        evaluations.append(
            Evaluation(
                id=f"eval:{id}",
                question=question,
                answerable=True,
                expected_answer=names[path[-1]],
                expected_path=path,
                source_document_ids=sorted({f.source_document_id for f in selected}),
                supporting_fact_ids=fact_ids,
            )
        )

    evaluation("one-hop", "Which project does Priya manage?", ["fact:001"])
    evaluation(
        "two-hop", "Which database does the project managed by Priya use?", ["fact:001", "fact:003"]
    )
    evaluation(
        "three-hop",
        "Which cloud platform hosts the database used by the project managed by Priya?",
        ["fact:001", "fact:003", "fact:005"],
    )
    evaluation(
        "atlas-east",
        "Which cloud platform hosts the database used by Morgan's project?",
        ["fact:006", "fact:009", "fact:010"],
    )
    evaluation(
        "lee-cedar",
        "Where is the database of the project managed by Cedar employee 002 Lee Chen hosted?",
        ["fact:016", "fact:019", "fact:020"],
    )
    evaluation(
        "lee-tidal",
        "Where is the database of the project managed by Tidal employee 001 Lee Chen hosted?",
        ["fact:021", "fact:024", "fact:025"],
    )
    for id, question, reason in [
        ("unknown-manager", "Which project does Ivo manage?", "No management evidence for Ivo."),
        (
            "unknown-region",
            "Which AWS region hosts Atlas?",
            "Hosting platform is recorded; region is absent.",
        ),
        (
            "ambiguous-lee",
            "Which project does Lee Chen manage?",
            "Two distinct people share this name; clarification is required.",
        ),
    ]:
        evaluations.append(
            Evaluation(
                id=f"eval:{id}",
                question=question,
                answerable=False,
                expected_answer=None,
                expected_path=[],
                source_document_ids=[],
                supporting_fact_ids=[],
                reason=reason,
            )
        )
    validate_evaluations(fixture, evaluations)
    return fixture, evaluations


def main():
    fixture, evaluations = build()
    (ROOT / "data/fixtures/corporate.json").write_text(fixture.model_dump_json(indent=2) + "\n")
    (ROOT / "data/evaluation/questions.json").write_text(
        json.dumps([e.model_dump(mode="json") for e in evaluations], indent=2) + "\n"
    )
    print("Wrote deterministic fictional fixture and evaluation examples")


if __name__ == "__main__":
    main()
