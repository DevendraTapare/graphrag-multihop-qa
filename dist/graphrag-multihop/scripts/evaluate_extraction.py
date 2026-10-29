import json

from app.evaluation.extraction import evaluate
from app.extraction.pipeline import ExtractionPipeline
from app.graph.fixtures import ROOT


def main():
    result = evaluate(ExtractionPipeline())
    (ROOT / "reports/extraction-evaluation.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
