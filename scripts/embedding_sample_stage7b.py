"""Compare trusted cached encoder output across the old and candidate environments."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))


def main():
    from app.vector.embedding import MiniLM

    model = MiniLM()
    try:
        vectors = model.encode(
            [
                "Priya at Lumen Orchard manages Project Atlas.",
                "Project Atlas uses PostgreSQL.",
                "PostgreSQL is hosted on AWS.",
            ]
        )
        Path(sys.argv[1]).write_text(
            json.dumps({"embedding_version": model.version, "vectors": vectors}), encoding="utf-8"
        )
    finally:
        model.close()


if __name__ == "__main__":
    main()
