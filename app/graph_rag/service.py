import time
from collections import Counter
from uuid import uuid4

from app.extraction.models import ChunkOptions
from app.extraction.pipeline import ExtractionPipeline
from app.graph_rag.interpretation import interpret
from app.graph_rag.linking import EntityLinker
from app.graph_rag.models import (
    Budget,
    EvidencePath,
    GraphFailure,
    GraphRequest,
    GraphResponse,
    ReasoningStep,
)
from app.graph_rag.provenance import GraphProvenance, InvalidEvidence
from app.graph_rag.repository import GraphPolicy, GraphRepository, edge_key


class GraphOnlyService:
    def __init__(self, repository, pipeline, request_timeout=20, max_answers=10, max_bytes=65536):
        self.repo, self.pipeline = repository, pipeline
        self.linker = EntityLinker(pipeline.registry)
        self.provenance = GraphProvenance(pipeline, repository.policy, max_bytes)
        self.request_timeout, self.max_answers = request_timeout, max_answers

    def query(self, question, max_hops=3, request_id=None):
        request = GraphRequest(question=question, max_hops=max_hops)
        rid = request_id or uuid4().hex
        started = time.perf_counter()
        budget = Budget(self.request_timeout)
        times = {
            k: 0.0
            for k in (
                "parsing",
                "entity_linking",
                "traversal",
                "provenance",
                "selection",
                "revalidation",
                "generation",
            )
        }
        plan = resolution = None
        raw, valid, paths, chunks = [], [], [], {}
        diagnostics = Counter()
        discarded = 0

        def response(reason, answers=(), citations=()):
            budget.remaining()
            return GraphResponse(
                answer="; ".join(e.name for e in answers) if answers else None,
                answers=tuple(answers),
                abstained=not bool(answers),
                reason=reason,
                request_id=rid,
                plan=plan,
                resolution=resolution,
                hop_count=plan.hop_count if plan else 0,
                reasoning_path=paths[0].steps if len(paths) == 1 and answers else (),
                reasoning_paths=tuple(paths),
                citations=tuple(citations),
                evidence_chunks=tuple(chunks[k] for k in sorted(chunks)),
                candidate_path_count=len(raw),
                paths_discarded=discarded,
                diagnostics=dict(diagnostics),
                latency_ms={**times, "end_to_end": (time.perf_counter() - started) * 1000},
            )

        phase = time.perf_counter()
        plan = interpret(request.question)
        times["parsing"] = (time.perf_counter() - phase) * 1000
        if plan is None:
            return response("unsupported_question_grammar")
        if plan.hop_count > request.max_hops:
            return response("requested_hop_limit")
        phase = time.perf_counter()
        resolution = self.linker.resolve(plan)
        times["entity_linking"] = (time.perf_counter() - phase) * 1000
        if resolution.status != "resolved":
            return response("entity_" + resolution.status)
        if self.repo.policy.processing_version != self.pipeline.version:
            raise GraphFailure("graph_processing_configuration_stale")
        phase = time.perf_counter()
        raw, overflow = self.repo.capture(plan, resolution.canonical_id, budget)
        times["traversal"] = (time.perf_counter() - phase) * 1000
        diagnostics["complete_candidates"] = sum(row["depth"] == plan.hop_count for row in raw)
        if overflow:
            return response("candidate_limit_exceeded")
        phase = time.perf_counter()
        metadata = self.repo.metadata(raw, budget)
        document_cache, edge_cache = {}, {}
        for row in raw:
            budget.remaining()
            try:
                nodes = tuple(
                    self.provenance.entity(n, t)
                    for n, t in zip(row["nodes"], plan.node_types[: row["depth"] + 1], strict=True)
                )
                supports = []
                for j, edge in enumerate(row["edges"]):
                    step = plan.steps[j]
                    actual = (nodes[j].id, nodes[j + 1].id)
                    if step.direction == "incoming":
                        actual = actual[::-1]
                    if (edge["source"], edge["target"]) != actual or edge[
                        "kind"
                    ] != step.relation.value:
                        raise InvalidEvidence("relationship_direction_invalid")
                    key = edge_key(edge)
                    if key not in edge_cache:
                        try:
                            edge_cache[key] = self.provenance.edge(
                                edge, metadata.get(key), document_cache, budget
                            )
                        except InvalidEvidence as exc:
                            edge_cache[key] = exc
                    evidence = edge_cache[key]
                    if isinstance(evidence, InvalidEvidence):
                        raise evidence
                    cite, chunk = evidence
                    supports.append(cite)
                    chunks[(chunk.document_id, chunk.chunk_id)] = chunk
                valid.append((nodes, tuple(supports)))
            except InvalidEvidence as exc:
                discarded += 1
                diagnostics[exc.reason] += 1
        diagnostics["edges_checked"] = len(edge_cache)
        diagnostics["provenance_rejections"] = sum(
            isinstance(v, InvalidEvidence) for v in edge_cache.values()
        )
        times["provenance"] = (time.perf_counter() - phase) * 1000
        phase = time.perf_counter()
        # Deduplicate logical paths while retaining every independent edge assertion.
        grouped = {}
        for nodes, supports in valid:
            ids = tuple(n.id for n in nodes)
            if ids not in grouped:
                grouped[ids] = (nodes, [{} for _ in supports])
            for j, cite in enumerate(supports):
                grouped[ids][1][j][cite.fact_id] = cite
        for ids, (nodes, evidence) in sorted(grouped.items()):
            if len(ids) != plan.hop_count + 1:
                continue
            steps = []
            for j, step in enumerate(plan.steps):
                stored = (
                    (ids[j], ids[j + 1]) if step.direction == "outgoing" else (ids[j + 1], ids[j])
                )
                steps.append(
                    ReasoningStep(
                        source=nodes[j],
                        target=nodes[j + 1],
                        relation=step.relation,
                        direction=step.direction,
                        stored_source_id=stored[0],
                        stored_target_id=stored[1],
                        supports=tuple(evidence[j][k] for k in sorted(evidence[j])),
                    )
                )
            paths.append(EvidencePath(nodes=nodes, steps=tuple(steps), hop_count=plan.hop_count))
        diagnostics["validated_complete_paths"] = len(paths)
        # Every known validated branch must have a validated next step. A complete
        # path cannot mask another managed project's missing intermediate evidence.
        missing_branch = any(
            len(ids) <= plan.hop_count
            and not any(len(other) == len(ids) + 1 and other[:-1] == ids for other in grouped)
            for ids in grouped
        )
        answer_map = {p.nodes[-1].id: p.nodes[-1] for p in paths}
        times["selection"] = (time.perf_counter() - phase) * 1000
        # Re-read actual paths AND source state, including prefixes and alternatives.
        # A concurrent correction may add a conflict as well as remove old support.
        if raw:
            phase = time.perf_counter()
            self.repo.recheck(plan, resolution.canonical_id, raw, metadata, budget)
            times["revalidation"] = (time.perf_counter() - phase) * 1000
        if missing_branch:
            return response("missing_intermediate_evidence")
        if not paths:
            return response("invalid_evidence" if discarded else "no_complete_path")
        if len(answer_map) > self.max_answers:
            return response("answer_limit_exceeded")
        if len(answer_map) > 1 and not plan.multiple:
            return response("conflicting_answers")
        phase = time.perf_counter()
        answers = sorted(answer_map.values(), key=lambda e: (e.name.casefold(), e.id))
        citations = {c.fact_id: c for p in paths for step in p.steps for c in step.supports}
        times["generation"] = (time.perf_counter() - phase) * 1000
        return response("supported", answers, [citations[k] for k in sorted(citations)])


def build_graph_service(database, settings, policy=None):
    pipeline = ExtractionPipeline(
        ChunkOptions(size=settings.ingestion_chunk_size, overlap=settings.ingestion_chunk_overlap)
    )
    repository = GraphRepository(
        database,
        policy or GraphPolicy.load(),
        settings.graph_max_candidates,
        settings.graph_query_timeout,
    )
    return GraphOnlyService(
        repository,
        pipeline,
        settings.graph_request_timeout,
        settings.graph_max_answers,
        settings.ingestion_max_bytes,
    )
