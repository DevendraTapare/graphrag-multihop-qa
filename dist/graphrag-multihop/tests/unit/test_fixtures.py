import copy

import pytest
from pydantic import ValidationError

from app.graph.fixtures import graph_rows, read_evaluations, read_fixture
from app.models.fixtures import Fixture, normalize_name, validate_evaluations
from scripts.build_fixtures import build


def test_checked_in_fixture_is_deterministic():
    built, evaluations = build()
    assert built == read_fixture()
    assert evaluations == read_evaluations()
    nodes, edges = graph_rows(built)
    assert len(nodes) == 50
    assert len(built.entities) == 26
    assert len(built.facts) == 30
    assert len({e["properties"]["id"] for e in edges}) == len(edges)
    assert graph_rows(built) == graph_rows(read_fixture())


def test_fixture_has_distractors_and_disconnected_people():
    fixture = read_fixture()
    lees = [e for e in fixture.entities if e.name == "Lee Chen"]
    assert len(lees) == 2 and lees[0].id != lees[1].id
    postgres = [e for e in fixture.entities if e.name == "PostgreSQL"]
    assert len(postgres) == 2 and postgres[0].scope != postgres[1].scope
    endpoints = {id for fact in fixture.facts for id in (fact.subject, fact.object)}
    assert "person:ivo" not in endpoints and "person:una" not in endpoints


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_node",
        "duplicate_fact",
        "missing_evidence",
        "wrong_direction",
        "invalid_quote",
        "bad_offset",
        "duplicate_logical_entity",
        "invalid_label",
        "invalid_relationship",
        "confidence",
        "extra_field",
        "naive_timestamp",
        "orphan_document",
        "blank_name",
        "missing_endpoint",
    ],
)
def test_invalid_fixture_rejected(mutation):
    value = copy.deepcopy(read_fixture().model_dump(mode="json"))
    match mutation:
        case "duplicate_node":
            value["entities"].append(value["entities"][0])
        case "duplicate_fact":
            value["facts"].append(value["facts"][0])
        case "missing_evidence":
            value["facts"][0]["source_chunk_id"] = "chunk:absent"
        case "wrong_direction":
            value["facts"][0]["subject"], value["facts"][0]["object"] = (
                value["facts"][0]["object"],
                value["facts"][0]["subject"],
            )
        case "invalid_quote":
            value["facts"][0]["quote"] = "Unsupported assertion"
        case "bad_offset":
            value["chunks"][0]["start"] = 2
        case "duplicate_logical_entity":
            value["entities"].append({**value["entities"][0], "id": "org:duplicate"})
        case "invalid_label":
            value["entities"][0]["label"] = "Person) MATCH (n) DELETE n"
        case "invalid_relationship":
            value["facts"][0]["predicate"] = "EXECUTE"
        case "confidence":
            value["facts"][0]["confidence"] = 1.1
        case "extra_field":
            value["facts"][0]["cypher"] = "RETURN 1"
        case "naive_timestamp":
            value["facts"][0]["created_at"] = "2026-01-01T00:00:00"
        case "orphan_document":
            value["chunks"][0]["document_id"] = "doc:absent"
        case "blank_name":
            value["entities"][0]["name"] = "   "
        case "missing_endpoint":
            value["facts"][0]["object"] = "project:absent"
    with pytest.raises(ValidationError):
        Fixture.model_validate(value)


def test_normalization_does_not_merge_scopes():
    assert normalize_name("  LEE   Chen ") == "lee chen"
    assert normalize_name("Ａｔｌａｓ") == "atlas"


def test_evaluation_evidence_and_hop_coverage():
    fixture, evaluations = read_fixture(), read_evaluations()
    validate_evaluations(fixture, evaluations)
    assert {len(e.supporting_fact_ids) for e in evaluations if e.answerable} == {1, 2, 3}
    assert sum(not e.answerable for e in evaluations) == 3
    priya = next(e for e in evaluations if e.id == "eval:three-hop")
    assert priya.expected_answer == "AWS"
    assert len(priya.source_document_ids) == 3


@pytest.mark.parametrize(
    "mutation", ["citations", "path", "answer", "unknown_fact", "unanswerable_claim"]
)
def test_invalid_evaluations_rejected(mutation):
    from app.models.fixtures import Evaluation

    evaluations = read_evaluations()
    index = -1 if mutation == "unanswerable_claim" else 0
    data = evaluations[index].model_dump()
    match mutation:
        case "citations":
            data["source_document_ids"] = []
        case "path":
            data["expected_path"] = ["person:ivo", "project:atlas"]
        case "answer":
            data["expected_answer"] = "Azure"
        case "unknown_fact":
            data["supporting_fact_ids"] = ["fact:absent"]
        case "unanswerable_claim":
            data["expected_answer"] = "AWS"
    evaluations[index] = Evaluation.model_validate(data)
    with pytest.raises(ValueError):
        validate_evaluations(read_fixture(), evaluations)
