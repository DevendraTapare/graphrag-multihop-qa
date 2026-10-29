"""New cross-mode identity and concurrent publication checks in a disposable database."""

import concurrent.futures

import pytest

from tests.integration.test_aligned import aligned_case as aligned_case
from tests.integration.test_graph_rag import graph_database as graph_database
from tests.integration.test_vector import isolated_vector_database as isolated_vector_database
from tests.integration.test_vector import real_minilm as real_minilm

pytestmark = pytest.mark.integration


def test_similar_name_distractor_does_not_cross_modes(aligned_case):
    c = aligned_case
    for mode in (c.graph(), c.hybrid()):
        r = mode.query("Which project does Mika Row manage?")
        assert r.answer == "Aspen East"
        assert all("Lina Shaw" not in cite.quote for cite in r.citations)
    r = c.vector.retrieve_vector_only("Which project does Mika Row manage?", 5)
    assert r.answer == "Aspen East"


def test_real_concurrent_idempotent_ingestion_and_queries(aligned_case):
    c = aligned_case
    before = c.graph().query("Which organization employs Lina Shaw?")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(c.add, c.docs[0].text, c.keys[c.docs[0].source_id])]
        futures += [
            pool.submit(c.graph().query, "Which organization employs Lina Shaw?") for _ in range(3)
        ]
        futures[0].result()
        for future in futures[1:]:
            response = future.result()
            assert response.answer == before.answer and response.citations == before.citations


def test_hybrid_unsupported_paraphrase_keeps_vector_candidate_diagnostic(aligned_case):
    c = aligned_case
    response = c.hybrid().query("Identify the cloud behind Lina Shaw's project database.")
    assert response.abstained and response.answer is None and not response.citations
    assert response.vector_evidence
