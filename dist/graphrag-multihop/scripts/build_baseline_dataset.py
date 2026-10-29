"""Explicit synthetic gold authoring. Does not call extraction, retrieval, or the answerer."""

import json

from app.extraction.documents import snapshot
from app.graph.fixtures import ROOT

VERSION = "multihop-vector-v1"
# Scenario identity, split, person, project, technology, platform, fictional organization.
SCENARIOS = [
    ("s01", "calibration", "Asha Rao", "Boreal", "CobaltDB", "AWS", "Orion Orchard"),
    ("s02", "calibration", "Ben Sato", "Saffron", "MariaDB", "Azure", "Kestrel Grove"),
    ("s03", "calibration", "Cora Vale", "Boreal East", "Memcached", "GCP", "Mica Harbor"),
    ("s04", "calibration", "Davi Moss", "Juniper", "ClickHouse", "AWS", "Sable Meadow"),
    ("s05", "calibration", "Elin Park", "Topaz", "Cassandra", "Azure", "Copper Nest"),
    ("s06", "calibration", "Femi Lake", "Willow", "SQLite", "GCP", "Lantern Vale"),
    ("s07", "held_out", "Rhea Sen", "Cedar Bridge", "OceanBase", "GCP", "Pebble Arc"),
    ("s08", "held_out", "Tomas Bell", "Indigo", "ScyllaDB", "AWS", "Silver Loom"),
    ("s09", "held_out", "Uma Frost", "Cedar Bridge West", "ArangoDB", "Azure", "Amber Quay"),
    ("s10", "held_out", "Vik Arden", "Marigold", "RocksDB", "GCP", "Birch Canvas"),
    ("s11", "held_out", "Jordan Vale (North employee 021)", "Quartz", "HBase", "AWS", "Aster Bay"),
    (
        "s12",
        "held_out",
        "Jordan Vale (South employee 022)",
        "Quartz South",
        "TiDB",
        "Azure",
        "Elm Crest",
    ),
]


def build():
    documents, facts, questions = [], [], []
    for sid, split, person, project, tech, cloud, org in SCENARIOS:
        held = split == "held_out"
        texts = [
            f"Project {project} is managed by {person}."
            if held
            else f"{person} manages Project {project}.",
            f"Project {project} utilizes its {tech} instance."
            if held
            else f"Project {project} uses its {tech} instance.",
            f"The {tech} instance for Project {project} runs on {cloud}."
            if held
            else f"The {tech} instance for Project {project} is hosted on {cloud}.",
            f"Project {project} is owned by {org}."
            if held
            else f"Project {project} belongs to {org}.",
            f"{person} is employed by {org}." if held else f"{person} works for {org}.",
        ]
        # Held-out layouts combine two statements and reverse their order; calibration
        # statements occupy independent documents. Both still need cross-document chains.
        layouts = [[0], [1], [2], [3], [4]] if not held else [[4, 0], [3, 1], [2]]
        # One manager has two valid intermediates. Gold requires both complete paths.
        if sid == "s01":
            texts += [
                f"{person} manages Project Boreal Annex.",
                "Project Boreal Annex uses its Firebird instance.",
                "The Firebird instance for Project Boreal Annex is hosted on Azure.",
                f"Project Boreal Annex belongs to {org}.",
            ]
            layouts += [[5], [6], [7], [8]]
        spans = {}
        for group_index, indices in enumerate(layouts):
            did = f"{sid}-source-{group_index + 1}"
            text = "\n".join(texts[n] for n in indices)
            doc = snapshot(f"stage3:{did}", f"stage3/{did}.txt", text)
            documents.append({"id": did, "split": split, "text": text})
            for n in indices:
                start = text.index(texts[n])
                fid = f"{sid}-fact-{n + 1}"
                fact = {
                    "id": fid,
                    "document_id": doc.id,
                    "source_id": doc.source_id,
                    "start": start,
                    "end": start + len(texts[n]),
                    "quote": texts[n],
                    "predicate": [
                        "MANAGES",
                        "USES",
                        "HOSTED_ON",
                        "BELONGS_TO",
                        "WORKS_FOR",
                        "MANAGES",
                        "USES",
                        "HOSTED_ON",
                        "BELONGS_TO",
                    ][n],
                    "subject": [
                        person,
                        project,
                        f"{tech}@{project}",
                        project,
                        person,
                        person,
                        "Boreal Annex",
                        "Firebird@Boreal Annex",
                        "Boreal Annex",
                    ][n],
                    "object": [
                        project,
                        f"{tech}@{project}",
                        cloud,
                        org,
                        org,
                        "Boreal Annex",
                        "Firebird@Boreal Annex",
                        "Azure",
                        org,
                    ][n],
                }
                facts.append(fact)
                spans[n] = fact

        if held:
            forms = [
                (f"Which project is led by {person}?", project, [[0]]),
                (f"Who employs {person}?", org, [[4]]),
                (f"What technology is used by Project {project}?", tech, [[1]]),
                (
                    f"Name the technology used by the project under {person}'s management?",
                    tech,
                    [[0, 1]],
                ),
                (f"Who owns the project under {person}'s management?", org, [[0, 3]]),
                (f"Where is the technology used by Project {project} hosted?", cloud, [[1, 2]]),
                (
                    f"What platform hosts the technology used by the project led by {person}?",
                    cloud,
                    [[0, 1, 2]],
                ),
                (
                    f"Where is the technology of the project under {person}'s management hosted?",
                    cloud,
                    [[0, 1, 2]],
                ),
            ]
        else:
            forms = [
                (f"Which project does {person} manage?", project, [[0]]),
                (f"Which organization employs {person}?", org, [[4]]),
                (f"Which database does Project {project} use?", tech, [[1]]),
                (f"Which database does the project managed by {person} use?", tech, [[0, 1]]),
                (f"Which organization owns the project managed by {person}?", org, [[0, 3]]),
                (
                    f"Which cloud platform hosts the database used by Project {project}?",
                    cloud,
                    [[1, 2]],
                ),
                (
                    "Which cloud platform hosts the database used by the project "
                    f"managed by {person}?",
                    cloud,
                    [[0, 1, 2]],
                ),
                (
                    f"What platform hosts the technology used by the project managed by {person}?",
                    cloud,
                    [[0, 1, 2]],
                ),
            ]
        for n, (question, answer, chains) in enumerate(forms):
            if sid == "s01" and n in {0, 3, 4, 6, 7}:
                second = {0: [5], 3: [5, 6], 4: [5, 8], 6: [5, 6, 7], 7: [5, 6, 7]}[n]
                chains.append(second)
                answer = {
                    0: "Boreal; Boreal Annex",
                    3: "CobaltDB; Firebird",
                    4: org,
                    6: "AWS; Azure",
                    7: "AWS; Azure",
                }[n]
            needed = sorted({index for chain in chains for index in chain})
            evidence = [spans[index] for index in needed]
            questions.append(
                {
                    "id": f"{sid}-q{n + 1:02}",
                    "split": split,
                    "question": question,
                    "answerable": True,
                    "expected_answer": answer,
                    "hops": max(map(len, chains)),
                    "required_document_ids": sorted({f["document_id"] for f in evidence}),
                    "supporting_fact_ids": [f["id"] for f in evidence],
                    "expected_evidence_chains": [
                        [spans[index]["id"] for index in chain] for chain in chains
                    ],
                    "tags": [
                        "synthetic",
                        "paraphrase" if n == 7 else "direct",
                        "multi_intermediate" if sid == "s01" else "single_intermediate",
                    ],
                }
            )

        # Dedicated missing-intermediate source: management and final platform exist,
        # but no source states that this project uses that technology.
        missing_id = f"{sid}-missing"
        missing_text = (
            f"Missing Owner {sid} manages Project {project} Sandbox.\n"
            f"The GhostDB instance for Project {project} Sandbox is hosted on {cloud}."
        )
        documents.append({"id": missing_id, "split": split, "text": missing_text})
        negatives = [
            (
                f"Which cloud platform hosts the database used by Project {project} Sandbox?",
                "missing_intermediate",
            ),
            (f"Which organization employs Unlisted Visitor {sid}?", "no_employment_evidence"),
        ]
        for n, (question, reason) in enumerate(negatives):
            questions.append(
                {
                    "id": f"{sid}-u{n + 1}",
                    "split": split,
                    "question": question,
                    "answerable": False,
                    "expected_answer": None,
                    "hops": 0,
                    "required_document_ids": [],
                    "supporting_fact_ids": [],
                    "expected_evidence_chains": [],
                    "reason": reason,
                    "tags": ["synthetic", reason],
                }
            )
        documents.append(
            {
                "id": f"{sid}-distractor",
                "split": split,
                "text": f"Project {project} Archive uses its TestStore instance. "
                f"The TestStore instance for Project {project} Archive is hosted on LocalRack. "
                "This archive is a different project.",
            }
        )

    for split in ("calibration", "held_out"):
        questions.append(
            {
                "id": f"{split}-ambiguous",
                "split": split,
                "question": "Which project does Jordan Vale manage?"
                if split == "held_out"
                else "Which project does Lee Chen manage?",
                "answerable": False,
                "expected_answer": None,
                "hops": 0,
                "required_document_ids": [],
                "supporting_fact_ids": [],
                "expected_evidence_chains": [],
                "reason": "ambiguous_person",
                "tags": ["synthetic", "entity_disambiguation"],
            }
        )
    return {"version": VERSION, "synthetic": True, "documents": documents}, {
        "version": VERSION,
        "synthetic": True,
        "facts": facts,
        "questions": questions,
        "disclosure": "Scenarios and question surfaces differ by split. "
        "Shared abstract relation grammar is intentional. Both splits were authored/inspected "
        "during development; held_out is a descriptive split, not a blind generalization estimate.",
    }


def main():
    corpus, gold = build()
    (ROOT / "data/fictional/stage3_corpus.json").write_text(
        json.dumps(corpus, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "data/evaluation/baseline_v1.json").write_text(
        json.dumps(gold, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"documents": len(corpus["documents"]), "questions": len(gold["questions"])}))


if __name__ == "__main__":
    main()
