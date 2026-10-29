"""Challenge runtime: source manifests only. No evaluation/generator/label imports."""

import json
import threading
from urllib.parse import urlparse

from app.aligned.graph import AlignedGraphService
from app.aligned.hybrid import HybridService
from app.aligned.integrity import SealedGraphRepository
from app.core.config import Settings
from app.db.neo4j import GraphDatabaseClient
from app.extraction.pipeline import ExtractionPipeline
from app.extraction.registry import EntityRegistry
from app.graph.fixtures import ROOT
from app.graph_rag.repository import GraphPolicy
from app.vector.embedding import MiniLM
from app.vector.repository import VectorRepository
from app.vector.retrieval import VectorOnlyService

DATA = ROOT / "data/stage6"
URI = "bolt://127.0.0.1:27689"


def challenge_settings():
    settings = Settings()
    # Fixed, loopback-only test endpoint. Compare normalized ports as well as names.
    for historical in (settings.neo4j_uri, settings.stage5_neo4j_uri):
        if urlparse(historical).port == urlparse(URI).port:
            raise ValueError("Challenge port overlaps a historical database")
    return settings.model_copy(update={"neo4j_uri": URI})


class Components:
    def __init__(self, database=None, model=None):
        self.settings = challenge_settings()
        self.db = database or GraphDatabaseClient(self.settings)
        self.model = model or MiniLM()
        self.vector = VectorOnlyService(VectorRepository(self.db, "stage6-challenge"), self.model)
        self._graph = self._hybrid = None
        self.lock = threading.Lock()

    @property
    def graph(self):
        with self.lock:
            if self._graph is None:
                registry = EntityRegistry(DATA / "registry.json")
                pipeline = ExtractionPipeline(registry=registry)
                corpus = json.loads((DATA / "corpus.json").read_text())
                if corpus["registry_version"] != registry.version:
                    raise ValueError("Challenge registry mismatch")
                if corpus["processing_version"] != pipeline.version:
                    raise ValueError("Challenge extraction mismatch")
                policy = GraphPolicy(tuple(corpus["source_ids"]), pipeline.version, None)
                self._graph = AlignedGraphService(
                    SealedGraphRepository(self.db, policy, 128, 10, corpus),
                    pipeline,
                    self.settings.graph_request_timeout,
                    10,
                )
            return self._graph

    @property
    def hybrid(self):
        graph = self.graph
        with self.lock:
            if self._hybrid is None:
                self._hybrid = HybridService(self.vector, graph, 60)
            return self._hybrid

    def query(self, mode, question):
        response = (
            self.vector.retrieve_vector_only(question, 5)
            if mode == "vector_only"
            else self.graph.query(question, 3)
            if mode == "graph_only"
            else self.hybrid.query(question, 5, 3)
        )
        return response.model_dump(mode="json")

    def close(self):
        self.model.close()
        self.db.close()


def api():
    from app.main import create_app

    return create_app(aligned=Components())
