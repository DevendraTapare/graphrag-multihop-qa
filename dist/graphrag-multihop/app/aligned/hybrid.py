"""Real vector candidates plus complete graph proof; deterministic evidence-only RRF."""

import re
import time

from app.aligned.models import FusedEvidence, HybridRequest, HybridResponse
from app.graph_rag.models import Budget


def fuse(vector_chunks, graph_chunks, rerank=True):
    vectors = {(c.document_id, c.chunk_id): i for i, c in enumerate(vector_chunks, 1)}
    graph = {(c.document_id, c.chunk_id): i for i, c in enumerate(graph_chunks, 1)}
    rows = []
    for key in vectors.keys() | graph.keys():
        vr, gr = vectors.get(key), graph.get(key)
        score = (1 / (60 + vr) if vr else 0) + (1 / (60 + gr) if gr else 0)
        rows.append(
            FusedEvidence(
                document_id=key[0],
                chunk_id=key[1],
                vector_rank=vr,
                graph_rank=gr,
                rrf_score=score,
                sources=tuple(s for s, rank in (("vector", vr), ("graph", gr)) if rank),
            )
        )
    if rerank:
        rows.sort(key=lambda r: (-r.rrf_score, r.document_id, r.chunk_id))
    else:
        rows.sort(
            key=lambda r: (r.vector_rank or 10000, r.graph_rank or 10000, r.document_id, r.chunk_id)
        )
    return tuple(rows)


class HybridService:
    def __init__(self, vector, graph, request_timeout=60, expand=True, rerank=True):
        self.vector, self.graph = vector, graph
        self.request_timeout, self.expand, self.rerank = request_timeout, expand, rerank
        self.patterns = []
        for entry in graph.pipeline.registry.entries.values():
            self.patterns.append(
                (
                    entry,
                    re.compile(
                        r"(?<!\w)(?:"
                        + "|".join(
                            re.escape(a) for a in sorted(entry.aliases, key=len, reverse=True)
                        )
                        + r")(?!\w)",
                        re.I,
                    ),
                )
            )

    def discover_candidates(self, chunks):
        candidates = []
        for rank, chunk in enumerate(chunks, 1):
            matches = []
            for entry, pattern in self.patterns:
                if not self.expand and entry.entity.id.startswith("discovered:"):
                    continue
                matches.extend((m.start(), m.end(), entry) for m in pattern.finditer(chunk.text))
            matches.sort(key=lambda m: (m[0], -(m[1] - m[0]), m[2].entity.id))
            selected, seen = [], set()
            for start, end, entry in matches:
                if any(start < b and a < end and (start, end) != (a, b) for a, b in selected):
                    continue
                # A known prefix is not proof of an unknown longer identity or qualifier.
                if re.match(r" (?:[A-Z][\w-]*|\([^)]*\))", chunk.text[end:]):
                    continue
                selected.append((start, end))
                if entry.entity.id in seen:
                    continue
                seen.add(entry.entity.id)
                candidates.append(
                    {
                        "canonical_id": entry.entity.id,
                        "type": entry.entity.label.value,
                        "document_id": chunk.document_id,
                        "chunk_id": chunk.chunk_id,
                        "vector_rank": rank,
                    }
                )
        return candidates

    def query(self, question, top_k=5, max_hops=3, request_id=None):
        request = HybridRequest(question=question, top_k=top_k, max_hops=max_hops)
        started = time.perf_counter()
        budget = Budget(self.request_timeout)
        vector = self.vector.retrieve_vector_only(request.question, request.top_k)
        budget.remaining()
        phase = time.perf_counter()
        candidates = self.discover_candidates(vector.retrieved_chunks)
        discovery_ms = (time.perf_counter() - phase) * 1000
        budget.remaining()
        graph = self.graph.query(
            request.question, request.max_hops, request_id, request_timeout=budget.remaining()
        )
        phase = time.perf_counter()
        fused = fuse(vector.retrieved_chunks, graph.evidence_chunks, self.rerank)
        ranked_paths = list(graph.reasoning_paths)
        scores = {(r.document_id, r.chunk_id): r.rrf_score for r in fused}
        candidate_ranks = {}
        for candidate in candidates:
            key = candidate["canonical_id"]
            candidate_ranks[key] = min(candidate_ranks.get(key, 10000), candidate["vector_rank"])
        if self.rerank:

            def path_rank(path):
                keys = {(c.document_id, c.chunk_id) for s in path.steps for c in s.supports}
                mean = sum(scores[k] for k in sorted(keys)) / len(keys)
                return (
                    -mean,
                    min(candidate_ranks.get(n.id, 10000) for n in path.nodes),
                    tuple(n.id for n in path.nodes),
                )

            ranked_paths.sort(key=path_rank)
        citation_ranks = {(r.document_id, r.chunk_id): i for i, r in enumerate(fused)}
        citations = sorted(
            graph.citations,
            key=lambda c: (citation_ranks[(c.document_id, c.chunk_id)], c.start, c.end, c.fact_id),
        )
        fusion_ms = (time.perf_counter() - phase) * 1000
        budget.remaining()
        times = {
            "parsing": graph.latency_ms["parsing"],
            "embedding_generation": vector.latency_ms["query_embedding"],
            "vector_search": vector.latency_ms["vector_retrieval"],
            "vector_generation": vector.latency_ms["generation"],
            "candidate_generation": discovery_ms,
            "entity_linking": graph.latency_ms["entity_linking"],
            "graph_traversal": graph.latency_ms["traversal"],
            "provenance_validation": graph.latency_ms["provenance"],
            "graph_revalidation": graph.latency_ms["revalidation"],
            "fusion_ranking": fusion_ms,
            "answer_generation": graph.latency_ms["generation"],
            "end_to_end": (time.perf_counter() - started) * 1000,
        }
        return HybridResponse(
            **{
                **graph.model_dump(),
                "retrieval_mode": "hybrid_graph_vector",
                "generator": "deterministic_hybrid_v1",
                "vector_evidence": tuple(vector.retrieved_chunks),
                "reasoning_paths": tuple(ranked_paths),
                "citations": tuple(citations),
                "candidate_entities": tuple(candidates[:128]),
                "fused_evidence": fused,
                "vector_answer_candidate": vector.answer,
                "entity_expansion": self.expand,
                "evidence_reranking": self.rerank,
                "latency_ms": times,
            }
        )
