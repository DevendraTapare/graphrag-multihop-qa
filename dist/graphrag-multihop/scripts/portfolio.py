"""Real local portfolio demo and evaluation adapter over existing retrieval services.

Run from the clean publication directory. Source preparation never reads gold labels.
"""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from app.aligned.discovery import discover
from app.aligned.graph import AlignedGraphService
from app.aligned.hybrid import HybridService
from app.aligned.integrity import SealedGraphRepository
from app.core.config import Settings
from app.db.migrations import migrate
from app.db.neo4j import GraphDatabaseClient
from app.extraction.documents import fixture_documents
from app.extraction.models import SourceDocument
from app.extraction.pipeline import ExtractionPipeline
from app.extraction.registry import EntityRegistry
from app.graph.fixtures import ROOT
from app.graph.schema import DIRECTIONS, FactType
from app.graph_rag.models import Budget
from app.graph_rag.repository import GraphPolicy, edge_key
from app.vector.embedding import MiniLM
from app.vector.indexing import VectorIndexer
from app.vector.repository import VectorRepository
from app.vector.retrieval import VectorOnlyService

MODES = ("vector_only", "graph_only", "hybrid_graph_vector")
STATE = Path(os.environ.get("PORTFOLIO_STATE_DIR", ROOT / ".local/portfolio"))


def require_publication():
    if not (ROOT / "PUBLICATION.json").is_file():
        raise ValueError("Run portfolio commands from the clean publication directory")
    settings = Settings()
    if settings.app_env != "development" or urlparse(settings.neo4j_uri).hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ValueError("Portfolio demo requires a development database on loopback")
    if (urlparse(settings.neo4j_uri).port or 7687) in {7687, 17688, 27689}:
        raise ValueError("Portfolio writes cannot target a historical research port")
    return settings


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def source_documents(kind):
    if kind == "demo":
        return fixture_documents()
    documents = [
        SourceDocument.model_validate(d)
        for d in json.loads((ROOT / "data/stage6/sources.json").read_text(encoding="utf-8"))
    ]
    if kind == "smoke":
        documents = [d for d in documents if int(d.source_filename.split("/")[1]) in {0, 10, 20}]
    return documents


class Services:
    def __init__(self, kind):
        self.settings = require_publication()
        self.state = STATE / kind
        registry = EntityRegistry(self.state / "registry.json")
        self.pipeline = ExtractionPipeline(registry=registry)
        self.corpus = json.loads((self.state / "corpus.json").read_text(encoding="utf-8"))
        if (
            self.pipeline.version != self.corpus["processing_version"]
            or registry.version != self.corpus["registry_version"]
        ):
            raise ValueError("Prepared source publication version changed; prepare explicitly")
        self.db = GraphDatabaseClient(self.settings)
        self.model = MiniLM()
        self.vector = VectorOnlyService(VectorRepository(self.db, f"portfolio-{kind}"), self.model)
        policy = GraphPolicy(tuple(self.corpus["source_ids"]), self.pipeline.version, None)
        self.graph = AlignedGraphService(
            SealedGraphRepository(self.db, policy, 128, 10, self.corpus),
            self.pipeline,
            self.settings.graph_request_timeout,
            10,
        )
        self.hybrid = HybridService(self.vector, self.graph, 60)

    def query(self, mode, question):
        if mode not in MODES:
            raise ValueError("Unknown retrieval mode")
        value = (
            self.vector.retrieve_vector_only(question, 5)
            if mode == "vector_only"
            else self.graph.query(question, 3)
            if mode == "graph_only"
            else self.hybrid.query(question, 5, 3)
        )
        return value.model_dump(mode="json")

    def close(self):
        self.model.close()
        self.db.close()


def prepare(kind):
    settings = require_publication()
    documents = source_documents(kind)  # Source files only; no label or answer-key read.
    state = STATE / kind
    state.mkdir(parents=True, exist_ok=True)
    discovery = discover(documents)
    path = state / "registry.json"
    path.write_text(discovery.registry.model_dump_json(indent=2) + "\n", encoding="utf-8")
    pipeline = ExtractionPipeline(registry=EntityRegistry(path))
    assertions = []
    for doc in documents:
        _, _, proof = pipeline.extract(doc)
        assertions.extend(
            {
                "id": f.id,
                "kind": f.candidate.predicate.value,
                "source": f.subject_id,
                "target": f.object_id,
                "source_id": doc.source_id,
                "document_id": doc.id,
                "content_hash": doc.content_hash,
            }
            for f in proof.facts
        )
    corpus = {
        "source_ids": sorted(d.source_id for d in documents),
        "processing_version": pipeline.version,
        "registry_version": pipeline.registry.version,
        "documents": [
            {"source_id": d.source_id, "document_id": d.id, "content_hash": d.content_hash}
            for d in documents
        ],
        "assertions": sorted(assertions, key=lambda f: f["id"]),
    }
    dump(state / "corpus.json", corpus)
    db = GraphDatabaseClient(settings, write_retry_time=3)
    try:
        migrate(db)
        from app.repositories.ingestion import IngestionRepository
        from app.services.ingestion import IngestionService

        ingestion = IngestionService(IngestionRepository(db, pipeline))
        for doc in documents:
            ingestion.ingest(doc, lambda doc=doc: doc)
    finally:
        db.close()
    services = Services(kind)
    try:
        first = VectorIndexer(services.vector.repo, services.model).index(
            corpus["source_ids"], pipeline.version
        )
        repeated = VectorIndexer(services.vector.repo, services.model).index(
            corpus["source_ids"], pipeline.version
        )
        if not repeated["cached"] or first["build_id"] != repeated["build_id"]:
            raise ValueError("Non-idempotent vector publication")
        audit = audit_provenance(services)
        result = {
            "kind": kind,
            "source_documents": len(documents),
            "accepted_facts": len(assertions),
            "index": first,
            "repeat_index_cached": True,
            "provenance": audit,
            "source_only": True,
        }
        dump(state / "build.json", result)
        return result
    finally:
        services.close()


def audit_provenance(services):
    rows = services.db.execute(
        "MATCH (a:GraphNode)-[r]->(b:GraphNode) WHERE r.id IN $ids "
        "RETURN {properties:properties(a),labels:labels(a)} AS a, "
        "{properties:properties(b),labels:labels(b)} AS b, "
        "{source:a.id,target:b.id,kind:type(r),properties:properties(r)} AS edge",
        {"ids": [a["id"] for a in services.corpus["assertions"]]},
        timeout=30,
    )
    if len(rows) != len(services.corpus["assertions"]):
        raise ValueError("Missing prepared facts")
    budget, cache = Budget(120), {}
    metadata = services.graph.repo.metadata([{"edges": [r["edge"]]} for r in rows], budget)
    for row in rows:
        source, target = DIRECTIONS[FactType(row["edge"]["kind"])]
        services.graph.provenance.entity(row["a"], source)
        services.graph.provenance.entity(row["b"], target)
        services.graph.provenance.edge(row["edge"], metadata[edge_key(row["edge"])], cache, budget)
    return {"facts_checked": len(rows), "failures": 0}


def demo(output):
    services = Services("demo")
    person = "Priya (Lumen employee 001)"
    cases = [
        ("one_hop", f"Which project does {person} manage?", "Atlas"),
        ("two_hop", f"Which database does the project managed by {person} use?", "PostgreSQL"),
        (
            "three_hop",
            f"Which cloud platform hosts the database used by the project managed by {person}?",
            "AWS",
        ),
        ("vector_one_hop", "Which database does Project Atlas use?", "PostgreSQL"),
        ("unknown", "Which organization employs Nia Unlisted?", None),
        ("ambiguous", "Which project does Lee Chen manage?", None),
        ("missing_evidence", "Which organization employs Ivo?", None),
        ("unsupported_grammar", "Identify the cloud behind Priya's project database.", None),
    ]
    responses = []
    try:
        for label, question, expected in cases:
            for mode in MODES:
                response = services.query(mode, question)
                # Demo expectations are assertions AFTER real retrieval, never runtime inputs.
                if mode != "vector_only" or label in {
                    "vector_one_hop",
                    "unknown",
                    "ambiguous",
                    "missing_evidence",
                    "unsupported_grammar",
                }:
                    if response["answer"] != expected:
                        raise ValueError(f"Demo mismatch: {label}/{mode}: {response['answer']!r}")
                if label == "three_hop" and mode != "vector_only":
                    if not response["reasoning_paths"] or response["hop_count"] != 3:
                        raise ValueError("Actual three-hop proof missing")
                responses.append(
                    {"case": label, "mode": mode, "question": question, "response": response}
                )
        value = {
            "real_neo4j": True,
            "simulated_results": False,
            "cases": len(cases),
            "requests": len(responses),
            "source_only_build": json.loads(
                (services.state / "build.json").read_text(encoding="utf-8")
            ),
            "responses": responses,
            "provenance": audit_provenance(services),
        }
        dump(output, value)
        return {"cases": len(cases), "requests": len(responses), "verified": True}
    finally:
        services.close()


def evaluate(kind, output):
    if kind not in {"smoke", "challenge"}:
        raise ValueError("Evaluation requires --dataset smoke or --dataset challenge")
    from app.evaluation.baseline import measure
    from scripts.evaluate_stage5 import graph_chain, normalize

    labels = json.loads((ROOT / "data/stage6/labels.json").read_text(encoding="utf-8"))
    questions = labels["questions"]
    if kind == "smoke":
        selected = {f"s6-{world:02}-{q}" for world in (0, 10, 20) for q in (0, 3, 7)}
        questions = [q for q in questions if q["id"] in selected]
    services = Services(kind)
    rows = []
    try:
        for mode in MODES:
            for q in questions:
                response = services.query(mode, q["question"])
                metrics = measure(q, labels["facts"], normalize(response, mode))
                rows.append(
                    {
                        "id": q["id"],
                        "mode": mode,
                        "question": q["question"],
                        "answerable": q["answerable"],
                        **metrics,
                        "validated_graph_chain": graph_chain(q, labels["facts"], response)
                        if mode != "vector_only"
                        else None,
                        "response": response,
                    }
                )
        value = {
            "kind": kind,
            "questions": len(questions),
            "requests": len(rows),
            "rows": rows,
            "historical_results_overwritten": False,
            "note": "Smoke subset is a functional reproduction check, not the 180-question score",
        }
        dump(output, value)
        return {
            "kind": kind,
            "questions": len(questions),
            "requests": len(rows),
            "unsupported_answers": sum(r["unsupported_answer"] for r in rows),
        }
    finally:
        services.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "demo", "evaluate"])
    parser.add_argument("--dataset", choices=["demo", "smoke", "challenge"], default="demo")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        value = prepare(args.dataset)
    elif args.output is None or args.output.exists():
        parser.error("Provide a new --output path; measured outputs cannot be overwritten")
    elif args.command == "demo":
        value = demo(args.output)
    else:
        value = evaluate(args.dataset, args.output)
    print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
