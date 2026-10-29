"""A bounded source-derived publication seal; never supplies answers or paths."""

from app.graph.schema import FactType
from app.graph_rag.models import GraphFailure
from app.graph_rag.repository import GraphRepository


class SealedGraphRepository(GraphRepository):
    def __init__(self, database, policy, max_candidates=128, query_timeout=10, corpus=None):
        super().__init__(database, policy, max_candidates, query_timeout)
        if corpus is None or len(corpus["documents"]) > 256 or len(corpus["assertions"]) > 2048:
            raise ValueError("Invalid aligned corpus seal")
        self.corpus = corpus

    def verify_publication(self, budget):
        rows = self.read(
            "UNWIND $sources AS ref OPTIONAL MATCH (s:IngestionSource {id:ref.source_id}) "
            "OPTIONAL MATCH (i:Ingestion {id:s.current_run_id}) "
            "OPTIONAL MATCH (d:Document {id:i.document_id}) "
            "RETURN ref.source_id AS source_id,s.status AS status,s.desired_run_id AS desired,"
            "s.current_run_id AS current,s.processing_version AS processing, "
            "s.content_hash AS content_hash,i.document_id AS document_id,i.status AS run_status,"
            "i.processing_version AS run_processing,i.content_hash AS run_hash,"
            "d.id AS actual_document",
            {"sources": self.corpus["documents"]},
            budget,
        )
        wanted = {d["source_id"]: d for d in self.corpus["documents"]}
        if len(rows) != len(wanted):
            raise GraphFailure("aligned_build_incomplete")
        runs = {}
        for row in rows:
            doc = wanted[row["source_id"]]
            if (
                row["status"] != "ready"
                or row["run_status"] != "ready"
                or row["current"] != row["desired"]
                or not row["current"]
                or row["processing"] != self.policy.processing_version
                or row["run_processing"] != self.policy.processing_version
                or row["document_id"] != doc["document_id"]
                or row["actual_document"] != doc["document_id"]
                or row["content_hash"] != doc["content_hash"]
                or row["run_hash"] != doc["content_hash"]
            ):
                raise GraphFailure("aligned_build_incomplete")
            runs[row["source_id"]] = row["current"]
        for kind in FactType:
            expected = {a["id"]: a for a in self.corpus["assertions"] if a["kind"] == kind.value}
            if not expected:
                continue
            actual = self.read(
                f"MATCH ()-[r:{kind.value}]->() WHERE r.id IN $ids "
                "RETURN r.id AS id,startNode(r).id AS source,endNode(r).id AS target,"
                "r.source_id AS source_id,r.source_document_id AS document_id,"
                "r.content_hash AS content_hash,r.ingestion_id AS run,"
                "r.processing_version AS processing,r.provenance_status AS proof",
                {"ids": list(expected)},
                budget,
            )
            if len(actual) != len(expected) or {r["id"] for r in actual} != set(expected):
                raise GraphFailure("aligned_build_incomplete")
            for row in actual:
                if (
                    row["run"] != runs.get(row["source_id"])
                    or row["processing"] != self.policy.processing_version
                    or row["proof"] != "verified_rule"
                    or any(row[k] != v for k, v in expected[row["id"]].items() if k != "kind")
                ):
                    raise GraphFailure("aligned_build_incomplete")

    def capture(self, plan, start, budget):
        # Called initially and during final revalidation. Missing root branches cannot hide.
        self.verify_publication(budget)
        return super().capture(plan, start, budget)
