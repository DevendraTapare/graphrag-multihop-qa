import time

from app.vector.answering import DeterministicAnswerer
from app.vector.embedding import MODEL
from app.vector.models import QueryRequest, QueryResponse, VectorFailure


class VectorOnlyService:
    def __init__(self, repository, embedder, answerer=None):
        self.repo, self.embedder = repository, embedder
        self.answerer = answerer or DeterministicAnswerer()

    def retrieve_vector_only(self, question, top_k=5):
        request = QueryRequest(question=question, top_k=top_k)
        start = time.perf_counter()
        try:
            vector = self.embedder.encode([request.question])[0]
        except VectorFailure as exc:
            if exc.category == "embedding_token_limit":
                raise VectorFailure("question_token_limit") from exc
            raise
        embedded = time.perf_counter()
        build, chunks = self.repo.search(vector, request.top_k, self.embedder.version)
        retrieved = time.perf_counter()
        answer, citations, reason = self.answerer.answer(request.question, chunks)
        finished = time.perf_counter()
        return QueryResponse(
            answer=answer,
            abstained=answer is None,
            reason=reason,
            retrieved_chunks=chunks,
            citations=citations,
            embedding_model=MODEL,
            embedding_version=self.embedder.version,
            corpus_build=build,
            latency_ms={
                "query_embedding": (embedded - start) * 1000,
                "vector_retrieval": (retrieved - embedded) * 1000,
                "generation": (finished - retrieved) * 1000,
                "end_to_end": (finished - start) * 1000,
            },
        )
