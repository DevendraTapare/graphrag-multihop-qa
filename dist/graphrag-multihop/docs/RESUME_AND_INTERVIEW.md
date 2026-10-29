# Resume and interview material

## Accurate resume bullets

- Built a local GraphRAG pipeline that extracts typed entities and relationships from fictional documents, stores source-backed facts in Neo4j, and validates one-, two- and three-hop reasoning paths before answering.
- Implemented real CPU MiniLM vector retrieval, bounded Cypher traversal and hybrid evidence fusion, with source hashes, quote offsets, ingestion versions, ambiguity handling and stale-publication checks.
- Designed and documented controlled retrieval comparisons: graph and hybrid answered 54/128 positives on a new synthetic challenge, while hybrid increased complete text-chain coverage to 86/128 without increasing final answer accuracy.
- Investigated concurrent database errors using exception-chain and embedding-lock instrumentation; a pool-size-only change reduced graph/hybrid errors from 56/100 and 17/100 to 0/100 in one repeated local burst workload, with high latency and sustained capacity still unverified.

Use the executed test counts in [STAGE7A_RELEASE_REPORT.md](STAGE7A_RELEASE_REPORT.md) if adding a testing bullet. Do not call the inspected Stage 5 result an independent 100% generalization score. Do not describe this as production deployed, LLM evaluated, externally benchmarked or GitHub CI verified.

## Simple explanation

I built a system that answers questions whose evidence is spread across documents. For example, one document says Priya manages Atlas, another says Atlas uses PostgreSQL, and a third says that database runs on AWS. The system builds those links into a graph, follows them, and shows the exact source text supporting each step. I compared that with ordinary vector search and a hybrid approach. The graph worked well when its extraction and question rules covered the case, but new wording caused many abstentions. The project demonstrates traceable retrieval and also makes those limits visible.

## Detailed explanation

Source snapshots have portable source IDs and content hashes. Sentence-aware chunking preserves offsets. A conservative source-only discovery pass extends a reviewed registry using entity type, aliases and organization/project scope. Extraction rules emit only five typed factual relationships. Each candidate must pass exact quote, offset, endpoint and rule replay checks before transactional ingestion publishes a current source run.

The vector branch embeds chunks with a pinned 384-dimensional MiniLM model and publishes a versioned Neo4j vector build. The graph branch interprets supported question forms into fixed relation sequences, resolves a unique start and executes parameterized Cypher with at most three hops. Actual paths are checked against current evidence, competing candidates and a source publication seal. Final revalidation closes common stale-data and candidate-set races. Hybrid retrieves vector evidence, expands entities, validates graph paths and combines evidence ranks, while requiring graph proof for the final deterministic answer.

Evaluation distinguishes correct positive answers, correct negative abstentions, evidence recall, complete text chains, validated graph chains, source citations and errors. The historical aligned corpus reached 96/96 positive correctness for graph/hybrid after both splits had been inspected. On the later controlled challenge both answered 54/128 positives; hybrid found more complete text chains but did not expand the answer grammar. Load experiments exposed connection acquisition and serialized embedding contention. The clean release isolates source, tests and documentation from credentials, private logs, models and database volumes.

## Technical questions and answers

1. **Why can vector retrieval struggle on multi-hop questions?** Similarity ranks individual passages, while the answer may require a complete connected evidence set. Finding a relevant first passage does not guarantee retrieval of the database and hosting links. In this implementation the deterministic text answerer's grammar also limits the final result, so retrieval failure and answerer failure must be separated.

2. **How does Cypher traversal work here?** A supported question selects an allowlisted typed sequence such as MANAGES → USES → HOSTED_ON. A fixed template binds the start identity as a parameter, returns actual nodes and relationships, and limits candidates. User text is never concatenated into executable Cypher, and no unrestricted variable-length traversal is exposed.

3. **Why retain three relationships rather than add a Priya-to-AWS shortcut?** The three relationships show which project and database connect the person to the platform. A shortcut without its own source proof would hide the inference and can become stale independently of the original facts.

4. **What is the difference between identity and a name?** Names are aliases. Two people can share Priya, and two project-specific database instances can both be named PostgreSQL. Entity type and organization/project scope are part of resolution. A bare ambiguous alias abstains instead of silently merging identities.

5. **How is extraction automatic?** Supported source sentence forms produce typed mentions and relation candidates; registry discovery derives additional scoped identities from those source sentences. No gold answer key is used for construction. This is rule-based automation with finite coverage, not general named entity recognition or unrestricted language understanding.

6. **What does a fact's provenance contain?** Source identity, immutable document ID/hash, current ingestion run, processing version, evidence chunk, exact quote and offsets. The validator replays the extraction rule on that span and checks the actual endpoint IDs and types. A stored edge alone is insufficient proof.

7. **Does provenance prove real-world truth?** No. It proves a checked relationship to the supplied source text under this pipeline's rules. Fictional source truth, extraction completeness and real-world correctness are separate issues.

8. **How do updates avoid stale answers?** A source has a desired/current ingestion run and explicit lifecycle state. Only complete current publications can be used. Derived facts and vector builds carry the source/version context, and graph proof plus final revalidation rejects superseded or incomplete evidence.

9. **Why revalidate just before answering?** A source or competing branch can change after initial capture. Rechecking the publication and candidate set avoids accepting a once-valid but now-stale path. It costs extra round trips; batching that preserves equivalent checks is future work.

10. **Why did Stage 4 graph accuracy collapse?** Its graph did not contain the corpus targeted by the 96 positive benchmark questions. Every starting entity was unregistered and 64 required facts were absent. It was a corpus-alignment failure, while a separate populated fixture still supported the Priya three-hop path.

11. **Why did Stage 5 reach 100% and Stage 6 not?** The aligned Stage 5 source/question set was inspected during development. Stage 6 introduced new source and question forms after a runtime freeze. Some needed facts were not extracted and many valid question forms were unsupported. Both stages are controlled synthetic experiments, but only the later one tests those specified new forms.

12. **What exactly does Stage 6 accuracy mean?** Graph/hybrid answered 54/128 final positives: 36/80 one-hop, 14/36 two-hop and 4/12 three-hop. All modes correctly abstained on 52 final negatives. Combining those gives graph/hybrid 106/180 overall correctness, which must not be substituted for positive accuracy.

13. **Why was vector at zero positive answers despite useful evidence?** Its frozen answerer did not support the new plural question forms. Complete text chains were retrieved for 58/128 positives. Zero answer accuracy therefore does not establish zero retrieval recall or an inherently poor embedding model.

14. **Why did hybrid add coverage without better answers?** It retrieved complete text chains for 86/128 positives, but final answers still required the same graph grammar and validated paths as graph-only. Missing relations and unsupported grammar were not repaired by rank fusion. Both modes had 54/128 validated chains and correct positives.

15. **Were the new questions independently held out?** They were internally controlled holdouts created after a runtime freeze, with novelty and label-access audits. The same author controlled generation, labels and implementation; grammar families overlap, and later inspection was possible. They were not externally administered or natural-world samples.

16. **Does a deterministic repeat justify confidence intervals?** It establishes repeatability on those inputs. Questions share worlds, facts and templates, so treating them as independent random samples would overstate confidence. The three-hop score has only 12 positive cases and cannot support a broad performance claim.

17. **What caused the 50-user errors?** The new controlled pool-ten repeat captured ConnectionAcquisitionTimeoutError beneath safe DatabaseUnavailable errors: 56 graph and 17 hybrid failures per 100 requests. Pool 50 removed those errors in the paired repeat, but graph p95 rose to 17.27 seconds. The historical 49/14 error counts remain unchanged and did not capture every original underlying trace.

18. **What else limited performance?** The one-CPU host saturated, embeddings were serialized behind one model lock and graph validation made repeated database calls. At pool 50 hybrid embedding-lock wait p95 was 15.02 seconds. Completed throughput includes errors, so failure-heavy runs cannot be advertised as higher useful capacity.

19. **What are the security boundaries?** Local loopback access, typed allowlists, parameterized query values, bounded paths, source proof and safe error messages. Document content is not executed and the API has no arbitrary Cypher or ingestion endpoint. There is no authentication, multi-tenant isolation or verified public deployment security.

20. **What would you improve next?** Use externally controlled realistic documents/questions; improve extraction and query-form coverage while measuring recall and unsupported outputs; batch proof-equivalent database reads; evaluate bounded HTTP admission and sustained load/recovery. Preserve the fixed baseline and compare changes on new held-out cases rather than tuning to final labels.

21. **What has actually been released?** A separate local publication directory with source, fictional datasets, primary evidence, tests, locked dependencies, Docker and CI configuration, a real Neo4j demo and honest documentation. No Git remote, commit, push, deployment or license selection was performed. Hosted CI remains unverified and publishing still needs the owner's decision.
