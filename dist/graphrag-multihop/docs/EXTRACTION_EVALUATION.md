# Extraction evaluation

The labeled set is `data/evaluation/extraction.json`, reproducibly authored by `scripts/build_extraction_evaluation.py`. Labels are explicit canonical IDs, entity spans/types, relationship endpoints, evidence spans, and expected abstentions. The authoring helper does not call the extractor or resolver to produce gold labels.

There are **53 documents**, **110 entity-mention examples**, and **32 positive relationship examples**. Ten cases target ambiguous identities; twelve target unsupported or misleading statements. Twenty-five cases are calibration and twenty-eight are held out from that split. Texts and case IDs do not overlap between the splits.

The cases include exact forms, supported and unsupported paraphrases, reordered sentences, negation, hypotheses, similar project names, multiple people called Priya or Lee, contradictory hosting sources, missing evidence, quoted/code examples, wrong endpoint types, reversed directions, and embedded prompt-like instructions.

Run without a database or network provider:

```powershell
uv run python -m scripts.evaluate_extraction
```

Results, raw counts, and per-case outcomes are written to `reports/extraction-evaluation.json`.

## Metric definitions

Entity extraction matches exact `(start, end, type)` tuples, including longer unknown typed candidates queued for review. Precision is TP/(TP+FP); recall is TP/(TP+FN). Entity extraction is distinct from acceptance of a canonical identity.

Relationships match accepted `(canonical subject, predicate, canonical object, evidence start, evidence end)` tuples. Ambiguous relationships should abstain and are not positive canonical triples. Canonical resolution accuracy counts correct end-to-end decisions on all gold mentions, including required abstention; a missed mention is incorrect. Incorrect merge count is the number of wrong canonical assignments, including assignment when abstention was required.

Unsupported accepted facts are accepted triples absent from gold. Provenance accuracy counts accepted facts with correct gold evidence, source ID, chunk reference, content hash, and processing version. A group with no predictions has undefined precision, represented as null rather than 100%.

## Measured results

| Metric | Calibration | Held-out split | Combined |
| --- | ---: | ---: | ---: |
| Documents | 25 | 28 | 53 |
| Entity precision | 100% (52/52) | 100% (58/58) | 100% (110/110) |
| Entity recall | 100% (52/52) | 100% (58/58) | 100% (110/110) |
| Relationship precision | 100% (15/15) | 100% (15/15) | 100% (30/30) |
| Relationship recall | 100% (15/15) | 88.24% (15/17) | 93.75% (30/32) |
| Canonical resolution accuracy | 100% | 100% | 100% |
| Incorrect canonical assignments | 0 | 0 | 0 |
| Unsupported accepted facts | 0 | 0 | 0 |
| Provenance accuracy | 100% | 100% | 100% |
| Rejected candidates | 14 | 20 | 34 |

The two relationship misses are `Priya oversees Project Atlas` and `Project Beacon depends on Redis`. Their entity mentions are recognized, but their paraphrases are outside the approved relation grammar. They remain false negatives in the report.

An initial run exposed a prefix-resolution bug on Atlas North. It was fixed and regression-tested. The held-out split was inspected during this debugging, so final figures are an engineering evaluation on separate synthetic cases, not a blind or independent generalization estimate. No additional real-world dataset or benchmark was run. The fixture registry, grammar, and synthetic examples intentionally share a small fictional domain; these figures must not be presented as general-purpose extraction performance.
