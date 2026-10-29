"""Lazy Stage 5 services against their own database and source-derived registry."""

import threading

from app.aligned.graph import build_aligned_service
from app.aligned.hybrid import HybridService
from app.db.neo4j import GraphDatabaseClient
from app.graph_rag.models import GraphFailure
from app.vector.embedding import MiniLM
from app.vector.repository import VectorRepository
from app.vector.retrieval import VectorOnlyService


class AlignedComponents:
    def __init__(self, settings):
        if settings.stage5_neo4j_uri == settings.neo4j_uri:
            raise ValueError("Stage 5 requires an isolated database URI")
        self.settings = settings
        self.db = GraphDatabaseClient(
            settings.model_copy(update={"neo4j_uri": settings.stage5_neo4j_uri})
        )
        self.model = MiniLM(
            settings.embedding_startup_timeout, settings.embedding_inference_timeout
        )
        self.vector = VectorOnlyService(VectorRepository(self.db, "stage5-aligned"), self.model)
        self._graph = self._hybrid = None
        self.lock = threading.Lock()

    @property
    def graph(self):
        with self.lock:
            if self._graph is None:
                try:
                    self._graph = build_aligned_service(self.db, self.settings)
                except (OSError, ValueError, KeyError) as exc:
                    raise GraphFailure("aligned_corpus_unavailable") from exc
            return self._graph

    @property
    def hybrid(self):
        graph = self.graph
        with self.lock:
            if self._hybrid is None:
                self._hybrid = HybridService(
                    self.vector, graph, self.settings.hybrid_request_timeout
                )
            return self._hybrid

    def close(self):
        self.model.close()
        self.db.close()
