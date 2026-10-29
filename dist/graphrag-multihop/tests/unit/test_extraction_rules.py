import pytest
from pydantic import ValidationError

from app.evaluation.extraction import evaluate, read_cases
from app.extraction.documents import fixture_documents, snapshot
from app.extraction.models import ChunkOptions, EntityCandidate, IngestionFailure
from app.extraction.pipeline import ExtractionPipeline
from app.extraction.registry import EntityRegistry
from scripts.build_extraction_evaluation import build_cases
from scripts.build_registry import build_registry


@pytest.fixture(scope="module")
def pipeline():
    return ExtractionPipeline()


def test_registry_and_gold_data_are_reproducible():
    assert build_registry() == EntityRegistry().data
    assert build_cases() == read_cases()
    cases = read_cases()
    assert sum(len(c["entities"]) for c in cases) >= 30
    assert sum(len(c["relations"]) for c in cases) >= 30
    assert sum("ambiguous_identity" in c["tags"] for c in cases) >= 10
    assert sum("unsupported" in c["tags"] for c in cases) >= 10
    calibration = {c["text"] for c in cases if c["split"] == "calibration"}
    held = {c["text"] for c in cases if c["split"] == "held_out"}
    assert not calibration.intersection(held)
    for case in cases:
        for e in case["entities"]:
            assert case["text"][e["start"] : e["end"]] == e["text"]
        for r in case["relations"]:
            assert case["text"][r["start"] : r["end"]] == r["evidence"]


def test_all_stage1_facts_can_be_recovered(pipeline):
    results = [pipeline.extract(d)[2] for d in fixture_documents()]
    assert sum(len(r.facts) for r in results) == 30
    assert {f.candidate.predicate.value for r in results for f in r.facts} == {
        "MANAGES",
        "WORKS_FOR",
        "USES",
        "HOSTED_ON",
        "BELONGS_TO",
    }


@pytest.mark.parametrize(
    "case",
    [c for c in read_cases() if "unsupported" in c["tags"] or "ambiguous_identity" in c["tags"]],
    ids=lambda c: c["id"],
)
def test_adversarial_and_ambiguous_cases_accept_no_facts(pipeline, case):
    document = snapshot(f"unit:{case['id']}", "fiction.txt", case["text"])
    assert pipeline.extract(document)[2].facts == []


def test_known_aliases_case_and_project_context(pipeline):
    document = snapshot(
        "unit:aliases", "aliases.txt", "PRIYA manages PROJECT ATLAS. Atlas uses Postgres."
    )
    facts = pipeline.extract(document)[2].facts
    assert [(f.subject_id, f.object_id) for f in facts] == [
        ("person:priya", "project:atlas"),
        ("project:atlas", "tech:postgres-atlas"),
    ]


def test_same_name_people_and_instances_remain_distinct(pipeline):
    document = snapshot(
        "unit:identity",
        "identity.txt",
        "Priya (Lumen employee 001) manages Project Atlas. "
        "Priya (Cedar employee 003) manages Project Atlas East. "
        "Atlas uses PostgreSQL. Atlas East uses PostgreSQL.",
    )
    facts = pipeline.extract(document)[2].facts
    assert {f.subject_id for f in facts if f.candidate.predicate == "MANAGES"} == {
        "person:priya",
        "person:priya-cedar",
    }
    assert {f.object_id for f in facts if f.candidate.predicate == "USES"} == {
        "tech:postgres-atlas",
        "tech:postgres-east",
    }


def test_unknown_longer_project_never_resolves_to_known_prefix(pipeline):
    document = snapshot("unit:prefix", "prefix.txt", "Project Atlas North uses Redis.")
    _, batch, result = pipeline.extract(document)
    assert next(e for e in batch.entities if e.label == "Project").mention == "Project Atlas North"
    assert not any(e.canonical_id == "project:atlas" for e in result.entities)
    assert any(r.reason == "unknown_identity" for r in result.rejections)


@pytest.mark.parametrize(
    "text,wrong_id",
    [
        ("Atlas North uses Redis.", "project:atlas"),
        ("Priya Kapoor works for Lumen Orchard.", "person:priya"),
        ("Morgan works for Cedar Kite West.", "org:cedar"),
    ],
)
def test_unknown_longer_untyped_names_are_not_merged(pipeline, text, wrong_id):
    document = snapshot("unit:longer", "longer.txt", text)
    result = pipeline.extract(document)[2]
    assert not any(e.canonical_id == wrong_id for e in result.entities)
    assert result.facts == []


def test_crlf_line_without_terminal_punctuation_is_supported(pipeline):
    document = snapshot("unit:crlf", "crlf.txt", "Priya manages Project Atlas\r\n")
    result = pipeline.extract(document)[2]
    assert len(result.facts) == 1
    assert result.facts[0].candidate.evidence == "Priya manages Project Atlas"


def test_overlap_does_not_duplicate_assertions():
    pipeline = ExtractionPipeline(ChunkOptions(size=90, overlap=40))
    document = snapshot(
        "unit:overlap",
        "overlap.txt",
        "Priya manages Project Atlas. Atlas uses PostgreSQL. "
        "The PostgreSQL instance for Project Atlas is hosted on AWS.",
    )
    chunks, _, result = pipeline.extract(document)
    assert len(chunks) > 1
    assert len(result.facts) == 3
    assert len({f.id for f in result.facts}) == 3


def test_no_partial_sentence_claim_when_chunk_is_too_small():
    pipeline = ExtractionPipeline(ChunkOptions(size=32, overlap=8))
    document = snapshot(
        "unit:long", "long.txt", "The PostgreSQL instance for Project Atlas is hosted on AWS."
    )
    assert pipeline.extract(document)[2].facts == []


def test_unicode_offsets_remain_original(pipeline):
    document = snapshot("unit:unicode", "unicode.txt", "Café 🧪\r\nPriya manages Project Atlas.")
    _, _, result = pipeline.extract(document)
    assert len(result.facts) == 1
    fact = result.facts[0].candidate
    assert document.text[fact.start : fact.end] == "Priya manages Project Atlas."
    assert fact.start == len("Café 🧪\r\n")


def test_unsupported_entity_label_fails_structured_contract():
    with pytest.raises(ValidationError):
        EntityCandidate(
            id="mention:test",
            mention="Priya",
            label="ExecuteSystemCommand",
            source_document_id="doc:test",
            source_chunk_id="chunk:test",
            start=0,
            end=5,
            extraction_version="rules:test",
        )


def test_extraction_evaluation_reports_observed_limits(pipeline):
    report = evaluate(pipeline)
    assert report["overall"]["unsupported_accepted_fact_count"] == 0
    assert report["overall"]["incorrect_merge_count"] == 0
    assert report["held_out"]["relationships"]["false_negative"] == 2
    assert report["held_out"]["relationships"]["true_positive"] == 15
    assert report["overall"]["entities"]["true_positive"] == 110


def test_resolution_uses_type_aware_aliases(pipeline):
    assert pipeline.registry.candidates("Person", "Atlas") == []
    assert len(pipeline.registry.candidates("Person", "Priya")) == 2
    document = snapshot("unit:ambiguous", "ambiguous.txt", "Priya.")
    _, batch, _ = pipeline.extract(document)
    with pytest.raises(IngestionFailure, match="ambiguous_identity"):
        pipeline.registry.resolve(batch.entities[0], document, batch.entities)
