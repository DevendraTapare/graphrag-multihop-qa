"""Reliability probe: caller supplies an empty HF_HOME; runtime must stay offline."""

from app.vector.embedding import MiniLM
from app.vector.models import VectorFailure


def main():
    model = MiniLM()
    try:
        model.encode(["Model unavailable probe"])
    except VectorFailure as exc:
        print(exc.category)
        if exc.category != "embedding_model_unavailable":
            raise SystemExit(1) from None
    else:
        raise SystemExit("Expected missing model to fail")
    finally:
        model.close()


if __name__ == "__main__":
    main()
