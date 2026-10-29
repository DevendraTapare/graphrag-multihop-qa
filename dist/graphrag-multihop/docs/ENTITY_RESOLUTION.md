# Conservative entity resolution

Canonical identity comes from `data/extraction/entity_registry.json`. This is a reviewed fictional alias registry, not an extraction evaluation answer key. It reuses all 26 Stage 1 entity IDs and adds one deliberately distinct person, `person:priya-cedar`.

Aliases normalize Unicode NFKC, case, and whitespace for matching. Matching is type-aware. A project alias cannot resolve to a person. The original mention and its exact source offsets remain unchanged.

Known aliases include `Atlas` / `Project Atlas`, `Postgres` / `PostgreSQL`, qualified employee names, and cloud platform aliases. Two projects with similar names and the two PostgreSQL deployment IDs remain separate. Longer unknown identities outrank registered prefixes: `Project Atlas North` is reviewed as unknown rather than shortened to Atlas; `Priya Kapoor` does not become Priya.

| Mention/context | Resolution |
| --- | --- |
| Priya manages Project Atlas | `person:priya`, using explicit project context confirmed by registry membership |
| Priya (Cedar employee 003) | `person:priya-cedar` |
| Priya without distinguishing context | Reject as ambiguous |
| Lee Chen (Cedar employee 002) | `person:lee-north` |
| Lee Chen (Tidal employee 001) | `person:lee-south` |
| Lee Chen works for Lumen Orchard | Reject: neither registered Lee has this identity context |
| Atlas uses PostgreSQL | `tech:postgres-atlas` |
| Atlas East uses PostgreSQL | `tech:postgres-east` |
| PostgreSQL is hosted on AWS, with no project context | Reject as ambiguous |

If an alias has multiple candidates, explicit unambiguous projects and organizations in the same statement can filter them using reviewed registry context. A technology shorthand can also use one unambiguous project in the document. A document containing multiple candidate projects does not supply this fallback. People never acquire an employer by traversing management or ownership edges.

Registry project membership is identity-disambiguation metadata, not an automatically asserted MANAGES or WORKS_FOR fact. Employment, management, use, ownership, and hosting still require their own explicit supported sentences. If a unique qualified identity makes a claim that differs from another source, the assertion retains its own evidence for review.

Unknown and ambiguous mentions are stored as rejected candidates with reason codes. No new canonical person, organization, or deployment is invented from raw text. Adding an identity or alias requires editing the controlled registry deliberately and rerunning tests. The registry content hash changes the processing version, so facts produced under an older mapping are excluded by a reader using the current pipeline.

The measured incorrect-merge metric counts wrong canonical assignments on labeled mentions, including assignment to a mention whose gold outcome is abstention. Zero measured incorrect merges applies only to the small synthetic evaluation set. It is not a guarantee for arbitrary real-world names or organizations.
