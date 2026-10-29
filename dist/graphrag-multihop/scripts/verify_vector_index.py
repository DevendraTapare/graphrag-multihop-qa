"""Audit real vectors, source identity, repeat indexing, and Stage 1–2 preservation."""

import json

from app.core.config import Settings
from app.extraction.models import ChunkOptions
from app.extraction.pipeline import ExtractionPipeline
from app.graph.fixtures import ROOT, read_evaluations, read_fixture
from app.repositories.ingestion import IngestionRepository
from app.services.ingestion_validation import validate_ingestion
from app.services.validation import validate_graph
from app.vector.embedding import DIMENSION, MODEL, REVISION, validate_vector
from app.vector.indexing import VectorIndexer
from scripts.vector import components, corpus_documents


def main():
    (ROOT / "reports/stage3").mkdir(parents=True, exist_ok=True)
    settings = Settings()
    db, model, repo = components(settings)
    try:
        pipeline = ExtractionPipeline(
            ChunkOptions(
                size=settings.ingestion_chunk_size, overlap=settings.ingestion_chunk_overlap
            )
        )
        documents = corpus_documents()
        sources = [d.source_id for d in documents]
        before = db.execute("MATCH (e:ChunkEmbedding) RETURN count(e) AS n")[0]["n"]
        repeated = VectorIndexer(repo, model).index(sources, pipeline.version)
        if not (repeated["cached"]):
            raise AssertionError()
        after = db.execute("MATCH (e:ChunkEmbedding) RETURN count(e) AS n")[0]["n"]
        if not (before == after):
            raise AssertionError()
        build = repo.current(model.version)
        vectors = repo.read(
            "MATCH (e:ChunkEmbedding {build_id:$build}) "
            "RETURN e.chunk_id AS chunk, e.embedding AS vector",
            {"build": build["id"]},
        )
        if not (len(vectors) == repeated["chunks"] == len({r["chunk"] for r in vectors})):
            raise AssertionError()
        for row in vectors:
            validate_vector(row["vector"])
        ingestion = IngestionRepository(db, pipeline)
        audits = [validate_ingestion(ingestion, d.source_id) for d in documents]
        stage1 = validate_graph(db, read_fixture(), read_evaluations())
        result = {
            "model": MODEL,
            "revision": REVISION,
            "embedding_version": model.version,
            "processing_version": pipeline.version,
            "build": repeated,
            "index": repo.require_index(),
            "vectors_checked": len(vectors),
            "dimension": DIMENSION,
            "all_finite_normalized": True,
            "canonical_chunk_ids_unique": True,
            "idempotent_repeat": before == after,
            "source_audits_passed": len(audits),
            "stage1": stage1,
            "schema": {
                "constraints": len(db.execute("SHOW CONSTRAINTS")),
                "indexes": len(db.execute("SHOW INDEXES")),
            },
        }
        (ROOT / "reports/stage3/index_verification.json").write_text(
            json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8"
        )
        print(
            json.dumps({k: v for k, v in result.items() if k not in {"index", "stage1"}}, indent=2)
        )
    finally:
        model.close()
        db.close()


if __name__ == "__main__":
    main()
