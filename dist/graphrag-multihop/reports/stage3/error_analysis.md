# Baseline error analysis

Scenarios and question surfaces differ by split. Shared abstract relation grammar is intentional. Both splits were authored/inspected during development; held_out is a descriptive split, not a blind generalization estimate.

At k=5, failures below distinguish incomplete retrieved evidence from generation failures. No GraphRAG result exists yet.

| Question | Hops | Complete evidence | Generator reason | Missing facts |
| --- | ---: | --- | --- | --- |
| s01-q04 | 2 | False | insufficient_evidence | s01-fact-2, s01-fact-7 |
| s01-q05 | 2 | False | insufficient_evidence | s01-fact-4, s01-fact-9 |
| s01-q06 | 2 | False | insufficient_evidence | s01-fact-2 |
| s01-q07 | 3 | False | insufficient_evidence | s01-fact-2, s01-fact-3, s01-fact-6, s01-fact-7, s01-fact-8 |
| s01-q08 | 3 | False | insufficient_evidence | s01-fact-2, s01-fact-3, s01-fact-7, s01-fact-8 |
| s02-q04 | 2 | False | insufficient_evidence | s02-fact-2 |
| s02-q05 | 2 | False | insufficient_evidence | s02-fact-4 |
| s02-q07 | 3 | False | insufficient_evidence | s02-fact-2 |
| s02-q08 | 3 | False | insufficient_evidence | s02-fact-2, s02-fact-3 |
| s03-q03 | 1 | False | insufficient_evidence | s03-fact-2 |
| s03-q04 | 2 | False | insufficient_evidence | s03-fact-2 |
| s03-q05 | 2 | False | insufficient_evidence | s03-fact-4 |
| s03-q06 | 2 | False | insufficient_evidence | s03-fact-2, s03-fact-3 |
| s03-q07 | 3 | False | insufficient_evidence | s03-fact-1, s03-fact-2, s03-fact-3 |
| s03-q08 | 3 | False | insufficient_evidence | s03-fact-2, s03-fact-3 |
| s04-q04 | 2 | False | insufficient_evidence | s04-fact-2 |
| s04-q05 | 2 | False | insufficient_evidence | s04-fact-4 |
| s04-q06 | 2 | False | insufficient_evidence | s04-fact-2 |
| s04-q07 | 3 | False | insufficient_evidence | s04-fact-2, s04-fact-3 |
| s04-q08 | 3 | False | insufficient_evidence | s04-fact-2, s04-fact-3 |
| s05-q04 | 2 | False | insufficient_evidence | s05-fact-2 |
| s05-q05 | 2 | False | insufficient_evidence | s05-fact-4 |
| s05-q07 | 3 | False | insufficient_evidence | s05-fact-1, s05-fact-2, s05-fact-3 |
| s05-q08 | 3 | False | insufficient_evidence | s05-fact-2, s05-fact-3 |
| s06-q05 | 2 | False | insufficient_evidence | s06-fact-4 |
| s06-q07 | 3 | False | insufficient_evidence | s06-fact-2 |
| s07-q04 | 2 | False | insufficient_evidence | s07-fact-2 |
| s07-q05 | 2 | False | insufficient_evidence | s07-fact-4 |
| s07-q07 | 3 | False | insufficient_evidence | s07-fact-2, s07-fact-3 |
| s07-q08 | 3 | False | insufficient_evidence | s07-fact-2, s07-fact-3 |
| s08-q04 | 2 | False | insufficient_evidence | s08-fact-2 |
| s08-q05 | 2 | False | insufficient_evidence | s08-fact-4 |
| s08-q07 | 3 | False | insufficient_evidence | s08-fact-2, s08-fact-3 |
| s08-q08 | 3 | False | insufficient_evidence | s08-fact-2, s08-fact-3 |
| s09-q04 | 2 | False | insufficient_evidence | s09-fact-2 |
| s09-q05 | 2 | False | insufficient_evidence | s09-fact-4 |
| s09-q06 | 2 | False | insufficient_evidence | s09-fact-3 |
| s09-q07 | 3 | False | insufficient_evidence | s09-fact-2, s09-fact-3 |
| s09-q08 | 3 | False | insufficient_evidence | s09-fact-2, s09-fact-3 |
| s10-q04 | 2 | False | insufficient_evidence | s10-fact-2 |
| s10-q05 | 2 | False | insufficient_evidence | s10-fact-4 |
| s10-q07 | 3 | False | insufficient_evidence | s10-fact-2, s10-fact-3 |
| s10-q08 | 3 | False | insufficient_evidence | s10-fact-2, s10-fact-3 |
| s11-q04 | 2 | False | insufficient_evidence | s11-fact-2 |
| s11-q05 | 2 | False | insufficient_evidence | s11-fact-4 |
| s11-q07 | 3 | False | insufficient_evidence | s11-fact-2, s11-fact-3 |
| s11-q08 | 3 | False | insufficient_evidence | s11-fact-2, s11-fact-3 |
| s12-q04 | 2 | False | insufficient_evidence | s12-fact-2 |
| s12-q05 | 2 | False | insufficient_evidence | s12-fact-4 |
| s12-q07 | 3 | False | insufficient_evidence | s12-fact-2, s12-fact-3 |
| s12-q08 | 3 | False | insufficient_evidence | s12-fact-2, s12-fact-3 |
