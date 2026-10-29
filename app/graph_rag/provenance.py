"""Validate actual stored assertions; fixture data is a proof contract, never a path lookup."""

from datetime import datetime

from app.extraction.models import (
    AcceptedFact,
    IngestionFailure,
    RelationCandidate,
    SourceDocument,
    stable_id,
    text_hash,
)
from app.graph.fixtures import graph_rows, read_fixture
from app.graph.schema import FactType
from app.graph_rag.models import Citation, EntityView, EvidenceChunk
from app.models.fixtures import normalize_name


class InvalidEvidence(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


class GraphProvenance:
    def __init__(self, pipeline, policy, max_bytes=65536):
        self.pipeline, self.policy, self.max_bytes = pipeline, policy, max_bytes
        nodes, edges = graph_rows(read_fixture())
        self.curated_nodes = {n["properties"]["id"]: n for n in nodes}
        self.curated_edges = {e["properties"]["id"]: e for e in edges}

    def entity(self, raw, expected):
        p = raw["properties"]
        entry = self.pipeline.registry.entries.get(p.get("id"))
        if (
            not entry
            or entry.entity.label != expected
            or set(raw["labels"]) != {"GraphNode", expected.value}
        ):
            raise InvalidEvidence("canonical_type_invalid")
        entity = entry.entity
        if entity.id in self.curated_nodes:
            if p != self.curated_nodes[entity.id]["properties"]:
                raise InvalidEvidence("canonical_identity_changed")
        elif (p.get("name"), p.get("scope"), p.get("normalized_name")) != (
            entity.name,
            entity.scope,
            normalize_name(entity.name),
        ):
            raise InvalidEvidence("canonical_identity_changed")
        return EntityView(
            id=entity.id, name=entity.name, entity_type=entity.label, scope=entity.scope
        )

    def edge(self, edge, meta, cache, budget):
        budget.remaining()
        p = edge["properties"]
        if not meta or not meta.get("document"):
            raise InvalidEvidence("source_document_missing")
        if not meta.get("chunk"):
            raise InvalidEvidence("source_chunk_missing")
        if set(meta["document_labels"]) != {"GraphNode", "Document"} or set(
            meta["chunk_labels"]
        ) != {"GraphNode", "Chunk"}:
            raise InvalidEvidence("source_labels_invalid")
        if p.get("extraction_method") == "manual_fixture":
            return self._curated(edge, meta)
        return self._automatic(edge, meta, cache, budget)

    def _curated(self, edge, meta):
        p, d, c = edge["properties"], meta["document"], meta["chunk"]
        expected = self.curated_edges.get(p.get("id"))
        if (
            self.policy.curated_fixture_id is None
            or p.get("fixture_id") != self.policy.curated_fixture_id
        ):
            raise InvalidEvidence("curated_source_not_allowed")
        actual = {
            "source": edge["source"],
            "target": edge["target"],
            "kind": edge["kind"],
            "properties": p,
        }
        if not expected or actual != expected or edge["kind"] not in {f.value for f in FactType}:
            raise InvalidEvidence("curated_fact_not_approved")
        for node, label in ((d, "Document"), (c, "Chunk")):
            known = self.curated_nodes.get(node.get("id"))
            if not known or known["label"] != label or known["properties"] != node:
                raise InvalidEvidence("curated_source_changed")
        if (
            c["document_id"] != d["id"]
            or d["text"][c["start"] : c["end"]] != c["text"]
            or p["quote"] not in c["text"]
        ):
            raise InvalidEvidence("curated_evidence_mismatch")
        links = {
            e["kind"]: e
            for e in self.curated_edges.values()
            if e["source"] == c["id"] and e["kind"] in {"PART_OF", "DERIVED_FROM"}
        }
        observed = [link for link in meta["links"] if link["kind"] is not None]
        if len(observed) != 2 or any(
            links.get(link["kind"])
            != {
                "kind": link["kind"],
                "source": c["id"],
                "target": link["target"],
                "properties": link["properties"],
            }
            for link in observed
        ):
            raise InvalidEvidence("source_chunk_orphaned")
        start = d["text"].find(p["quote"], c["start"], c["end"])
        citation = Citation(
            fact_id=p["id"],
            document_id=d["id"],
            chunk_id=c["id"],
            quote=p["quote"],
            start=start,
            end=start + len(p["quote"]),
            source_kind="curated",
            content_hash=text_hash(d["text"]),
            extraction_method="manual_fixture",
        )
        return citation, self._chunk(d, c, "curated")

    def _automatic(self, edge, meta, cache, budget):
        p, d, c, s, i = (
            edge["properties"],
            meta["document"],
            meta["chunk"],
            meta["source"],
            meta["run"],
        )
        if not s or not i or s.get("id") not in self.policy.sources:
            raise InvalidEvidence("source_not_in_corpus")
        if s.get("status") != "ready" or i.get("status") != "ready":
            raise InvalidEvidence("ingestion_not_ready")
        if (
            s.get("current_run_id") != i.get("id")
            or s.get("desired_run_id") != i.get("id")
            or p.get("ingestion_id") != i.get("id")
            or c.get("ingestion_id") != i.get("id")
        ):
            raise InvalidEvidence("source_version_stale")
        version = self.pipeline.version
        if version != self.policy.processing_version or any(
            item.get("processing_version") != version for item in (s, i, p, c)
        ):
            raise InvalidEvidence("processing_version_stale")
        if (
            s.get("id") != p.get("source_id")
            or s.get("id") != d.get("source_id")
            or s.get("id") != i.get("source_id")
            or i.get("document_id") != d.get("id")
            or c.get("document_id") != d.get("id")
            or p.get("source_document_id") != d.get("id")
            or p.get("source_chunk_id") != c.get("id")
        ):
            raise InvalidEvidence("source_identity_mismatch")
        if (
            p.get("extraction_method") != "deterministic_rules"
            or p.get("provenance_status") != "verified_rule"
            or any(item.get("content_hash") != d.get("content_hash") for item in (s, i, p, c))
        ):
            raise InvalidEvidence("source_hash_or_approval_invalid")
        if len(d.get("text", "").encode("utf-8")) > self.max_bytes:
            raise InvalidEvidence("source_payload_too_large")
        if text_hash(d["text"]) != d.get("content_hash"):
            raise InvalidEvidence("source_hash_or_approval_invalid")
        try:
            key = (d["id"], i["id"])
            if key not in cache:
                doc = SourceDocument.model_validate(
                    {k: v for k, v in d.items() if k in SourceDocument.model_fields}
                )
                chunks, batch, result = self.pipeline.extract(doc)
                expected = {
                    x.id: {
                        **x.model_dump(),
                        "ingestion_id": i["id"],
                        "origin": "automatic_ingestion",
                    }
                    for x in chunks
                }
                stored = meta["chunks"]
                if len(stored) != len(expected) or any(
                    expected.get(x.get("id")) != x for x in stored
                ):
                    raise InvalidEvidence("ingestion_chunks_incomplete")
                if i.get("expected_chunk_count") != len(chunks) or i.get("fact_count") != len(
                    result.facts
                ):
                    raise InvalidEvidence("ingestion_publication_incomplete")
                cache[key] = doc, chunks, batch, result
            doc, chunks, batch, _ = cache[key]
            chosen = next((x for x in chunks if x.id == c.get("id")), None)
            if (
                not chosen
                or {**chosen.model_dump(), "ingestion_id": i["id"], "origin": "automatic_ingestion"}
                != c
            ):
                raise InvalidEvidence("source_chunk_changed")
            candidate = RelationCandidate.model_validate_json(p["candidate_json"])
            fact = AcceptedFact(
                id=p["id"],
                source_id=p["source_id"],
                content_hash=p["content_hash"],
                processing_version=p["processing_version"],
                ingestion_version=p["ingestion_version"],
                subject_id=edge["source"],
                object_id=edge["target"],
                candidate=candidate,
                provenance_status=p["provenance_status"],
                created_at=datetime.fromisoformat(p["created_at"]),
            )
            self.pipeline.validator.verify_fact(fact, doc, chunks, batch.entities, version)
            expected_props = {
                "id": fact.id,
                "ingestion_id": i["id"],
                "source_id": doc.source_id,
                "source_document_id": candidate.source_document_id,
                "source_chunk_id": candidate.source_chunk_id,
                "content_hash": doc.content_hash,
                "processing_version": version,
                "ingestion_version": doc.ingestion_version,
                "quote": candidate.evidence,
                "evidence_start": candidate.start,
                "evidence_end": candidate.end,
                "extraction_method": candidate.extraction_method,
                "extraction_version": candidate.extraction_version,
                "rule_id": candidate.rule_id,
                "rule_score": candidate.rule_score,
                "provenance_status": "verified_rule",
                "created_at": fact.created_at.isoformat(),
                "candidate_json": candidate.model_dump_json(),
            }
            if p != expected_props or candidate.predicate.value != edge["kind"]:
                raise InvalidEvidence("fact_payload_mismatch")
            links = [link for link in meta["links"] if link["kind"] is not None]
            expected_links = {
                kind: {
                    "id": stable_id("auto-edge", kind, c["id"], d["id"]),
                    "ingestion_id": i["id"],
                    "method": "verbatim_excerpt",
                }
                for kind in ("PART_OF", "DERIVED_FROM")
            }
            if len(links) != 2 or any(
                link["target"] != d["id"] or link["properties"] != expected_links.get(link["kind"])
                for link in links
            ):
                raise InvalidEvidence("source_chunk_orphaned")
            budget.remaining()
            return Citation(
                fact_id=p["id"],
                document_id=d["id"],
                chunk_id=c["id"],
                quote=p["quote"],
                start=p["evidence_start"],
                end=p["evidence_end"],
                source_kind="automatic",
                source_id=s["id"],
                content_hash=doc.content_hash,
                processing_version=version,
                extraction_method="deterministic_rules",
            ), self._chunk(d, c, "automatic")
        except (IngestionFailure, ValueError, KeyError, TypeError) as exc:
            if isinstance(exc, InvalidEvidence):
                raise
            raise InvalidEvidence("automatic_fact_proof_invalid") from exc

    @staticmethod
    def _chunk(document, chunk, kind):
        return EvidenceChunk(
            document_id=document["id"],
            chunk_id=chunk["id"],
            start=chunk["start"],
            end=chunk["end"],
            text=chunk["text"],
            content_hash=text_hash(document["text"]),
            source_kind=kind,
        )
