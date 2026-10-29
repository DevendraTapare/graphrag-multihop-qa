"""Controlled warm batch indexing and concurrent service latency measurement."""

import concurrent.futures
import json
import time
from uuid import uuid4

from app.core.config import Settings
from app.evaluation.baseline import percentile
from app.graph.fixtures import ROOT
from app.vector.indexing import VectorIndexer
from app.vector.repository import VectorRepository
from app.vector.retrieval import VectorOnlyService
from scripts.vector import components


def main():
    (ROOT / "reports/stage3").mkdir(parents=True, exist_ok=True)
    db, model, repo = components(Settings())
    temporary = "benchmark-" + uuid4().hex[:12]
    build_id = None
    try:
        current = repo.current(model.version)
        model.encode(["Warm local indexing benchmark"])
        bench_repo = VectorRepository(db, temporary)
        started = time.perf_counter()
        summary = VectorIndexer(bench_repo, model).index(
            current["source_ids"], current["processing_version"]
        )
        elapsed = time.perf_counter() - started
        build_id = summary["build_id"]
        repeated = VectorIndexer(bench_repo, model).index(
            current["source_ids"], current["processing_version"]
        )
        if not (repeated["cached"] and repeated["build_id"] == build_id):
            raise AssertionError()
        result = {
            "corpus_build": current["id"],
            "embedding_version": model.version,
            "warm_batch_indexing": {
                "documents": summary["documents"],
                "chunks": summary["chunks"],
                "seconds": elapsed,
                "chunks_per_second": summary["chunks"] / elapsed,
                "embedding_batch_size": 32,
                "idempotent_repeat": True,
            },
        }
        # Remove only this script's unique temporary vector build before latency probes.
        cleanup(db, temporary, build_id)
        build_id = None
        service = VectorOnlyService(repo, model)
        q = "Which database does Project Atlas use?"
        for concurrency in (1, 4):
            started = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                responses = list(pool.map(lambda _: service.retrieve_vector_only(q, 5), range(24)))
            if not (all(r.answer == "PostgreSQL" for r in responses)):
                raise AssertionError()
            result[f"concurrency_{concurrency}"] = {
                "requests": len(responses),
                "top_k": 5,
                "seconds": time.perf_counter() - started,
                "latency_ms": {
                    key: {
                        "p50": percentile([r.latency_ms[key] for r in responses], 0.5),
                        "p95": percentile([r.latency_ms[key] for r in responses], 0.95),
                    }
                    for key in ("query_embedding", "vector_retrieval", "end_to_end")
                },
            }
        (ROOT / "reports/stage3/performance.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2))
    finally:
        try:
            if build_id:
                cleanup(db, temporary, build_id)
        finally:
            model.close()
            db.close()


def cleanup(db, corpus, build):
    db.execute("MATCH (e:ChunkEmbedding {build_id:$build}) DELETE e", {"build": build})
    db.execute("MATCH (b:VectorBuild {id:$build}) DELETE b", {"build": build})
    db.execute("MATCH (c:VectorCorpus {id:$corpus}) DELETE c", {"corpus": corpus})


if __name__ == "__main__":
    main()
