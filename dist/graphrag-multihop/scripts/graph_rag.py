"""Read-only deterministic graph interpretation, linking, and multi-hop query CLI."""

import argparse
import json

from pydantic import ValidationError

from app.core.config import Settings
from app.db.neo4j import DatabaseUnavailable, GraphDatabaseClient
from app.extraction.registry import EntityRegistry
from app.graph_rag.interpretation import interpret
from app.graph_rag.linking import EntityLinker
from app.graph_rag.models import GraphFailure, GraphRequest
from app.graph_rag.service import build_graph_service


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "link", "query"])
    parser.add_argument("--question", required=True)
    parser.add_argument("--max-hops", type=int, default=3)
    args = parser.parse_args()
    try:
        request = GraphRequest(question=args.question, max_hops=args.max_hops)
    except ValidationError:
        parser.error("Invalid question or hop count")
    plan = interpret(request.question)
    if args.command == "plan":
        print(
            json.dumps(
                {
                    "plan": plan.model_dump(mode="json") if plan else None,
                    "hop_count": plan.hop_count if plan else 0,
                    "status": "supported" if plan else "unsupported_question_grammar",
                },
                indent=2,
            )
        )
        return
    if args.command == "link":
        result = (
            EntityLinker(EntityRegistry()).resolve(plan).model_dump()
            if plan
            else {"status": "unsupported_question_grammar"}
        )
        print(json.dumps(result, indent=2))
        return
    settings = Settings()
    db = GraphDatabaseClient(settings)
    try:
        result = build_graph_service(db, settings).query(request.question, request.max_hops)
        print(result.model_dump_json(indent=2))
    except (DatabaseUnavailable, GraphFailure) as exc:
        category = exc.category if isinstance(exc, GraphFailure) else "database_unavailable"
        print(json.dumps({"error": category}))
        raise SystemExit(1) from None
    finally:
        db.close()


if __name__ == "__main__":
    main()
