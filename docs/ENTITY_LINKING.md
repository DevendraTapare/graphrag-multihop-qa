# Canonical question entity linking

Stage 4 reuses the unchanged 27-entry reviewed registry in `data/extraction/entity_registry.json`. Type-aware matching uses existing NFKC, case, and whitespace normalization. There is no fuzzy matching, first-result selection, identity creation, vector similarity, or preference for whichever candidate has a complete graph path.

The parser supplies a starting type and mention. The linker looks up exact aliases of that type, then applies explicit supported organization/project context against reviewed registry memberships. Unknown context returns `not_found`; unresolved context ambiguity returns `ambiguous`. Context narrows identity only; it does not establish a new factual relationship.

| Question mention/context | Result |
| --- | --- |
| Morgan as Person | `person:morgan` |
| Priya as Person | ambiguous: distinct Lumen and Cedar people |
| Priya (Lumen employee 001) | `person:priya` |
| Priya at Lumen Orchard | `person:priya` through explicit organization context |
| Priya (Cedar employee 003) | `person:priya-cedar` |
| Lee Chen | ambiguous: separate Cedar and Tidal people |
| Atlas / Atlas East as Project | separate canonical IDs |
| PostgreSQL / Postgres as Technology | ambiguous without deployment context |
| Postgres instance for Project Atlas East | `tech:postgres-atlas-east` |
| Unregistered synthetic benchmark person | not_found |

The resolution object contains status (`resolved`, `ambiguous`, or `not_found`), canonical ID when resolved, sorted candidate IDs, and a sanitized reason code. A registry resolution is followed by independent validation of actual Neo4j endpoint labels, ID, name, scope, and trusted identity properties. Altered or mismatched stored endpoints cannot supply an answer.

Supported examples can be inspected without a database:

```powershell
uv run python -m scripts.graph_rag plan --question 'Which project does Morgan manage?'
uv run python -m scripts.graph_rag link --question 'Which project does Priya manage?'
uv run python -m scripts.graph_rag link --question 'Which project does Priya at Lumen Orchard manage?'
```

The Stage 3 benchmark extension introduced identities beyond this registry. Stage 4 deliberately does not add aliases or identities using held-out labels. All 96 answerable benchmark starts lack registry coverage. One of two intended ambiguous-person benchmark cases is detectable (Lee Chen); the unregistered Jordan Vale case returns not_found. Zero wrong assignments with zero resolved benchmark starts is not evidence of perfect linking. Original-domain integration tests separately establish successful linking, context resolution, and preservation of ambiguity. See [evaluation](GRAPH_EVALUATION.md).
