"""Explicit Stage 5 vector_only, graph_only, hybrid_graph_vector query modes."""

import argparse
import json

from app.aligned.components import AlignedComponents
from app.aligned.models import HybridRequest
from app.core.config import Settings
from app.db.neo4j import DatabaseUnavailable
from app.graph_rag.models import GraphFailure
from app.vector.models import VectorFailure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=["vector_only", "graph_only", "hybrid_graph_vector"], required=True
    )
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-hops", type=int, default=3)
    args = parser.parse_args()
    request = HybridRequest(question=args.question, top_k=args.top_k, max_hops=args.max_hops)
    components = AlignedComponents(Settings())
    try:
        if args.mode == "vector_only":
            result = components.vector.retrieve_vector_only(request.question, request.top_k)
        elif args.mode == "graph_only":
            result = components.graph.query(request.question, request.max_hops)
        else:
            result = components.hybrid.query(request.question, request.top_k, request.max_hops)
        print(result.model_dump_json(indent=2))
    except (DatabaseUnavailable, GraphFailure, VectorFailure) as exc:
        error = getattr(exc, "category", "database_unavailable")
        print(json.dumps({"error": error}))
        raise SystemExit(1) from None
    finally:
        components.close()


if __name__ == "__main__":
    main()
