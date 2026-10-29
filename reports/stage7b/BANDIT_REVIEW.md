# Every Bandit finding and its disposition

Line numbers refer to the Stage 7A input. Final locations for retained findings are in the JSON review. Every finding is reachable only through a local developer tool or its import; none is on an application request path. Historical tools can write reports or operate on research databases and must not be used as the clean demo workflow. No Bandit rule was suppressed. See `bandit-review.json` for code context, exact per-row rationale and remediation.

| # | File:line | Rule | Severity/confidence | Assessment and remediation |
|---|---|---|---|---|
| 1 | `scripts/audit_stage6_labels.py:52` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 2 | `scripts/audit_stage6_labels.py:53` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 3 | `scripts/audit_stage6_labels.py:63` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 4 | `scripts/audit_stage6_labels.py:84` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 5 | `scripts/benchmark_vector.py:35` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 6 | `scripts/benchmark_vector.py:57` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 7 | `scripts/build_aligned.py:133` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 8 | `scripts/build_aligned.py:151` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 9 | `scripts/build_aligned.py:172` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 10 | `scripts/build_stage6.py:73` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 11 | `scripts/build_stage6.py:84` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 12 | `scripts/build_stage6.py:91` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 13 | `scripts/check_ci_results.py:4` | B405 | LOW/HIGH | Import warning; associated parser hardened. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 14 | `scripts/check_ci_results.py:8` | B314 | MEDIUM/HIGH | Real unnecessary XML parsing exposure; fixed. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 15 | `scripts/check_ci_results.py:9` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 16 | `scripts/check_ci_results.py:10` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 17 | `scripts/check_ci_results.py:16` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 18 | `scripts/compare_stage4.py:89` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 19 | `scripts/document_stage6.py:7` | B405 | LOW/HIGH | Import warning; associated parser hardened. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 20 | `scripts/document_stage6.py:37` | B314 | MEDIUM/HIGH | Real unnecessary XML parsing exposure; fixed. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 21 | `scripts/document_stage6.py:38` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 22 | `scripts/evaluate_stage5.py:142` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 23 | `scripts/evaluate_stage5.py:148` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 24 | `scripts/evaluate_stage5.py:271` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 25 | `scripts/evaluate_stage6.py:93` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 26 | `scripts/evaluate_stage6.py:95` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 27 | `scripts/evaluate_stage6.py:303` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 28 | `scripts/record_stage3_tests.py:4` | B405 | LOW/HIGH | Import warning; associated parser hardened. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 29 | `scripts/record_stage3_tests.py:10` | B314 | MEDIUM/HIGH | Real unnecessary XML parsing exposure; fixed. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 30 | `scripts/record_stage4.py:6` | B405 | LOW/HIGH | Import warning; associated parser hardened. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 31 | `scripts/record_stage4.py:80` | B314 | MEDIUM/HIGH | Real unnecessary XML parsing exposure; fixed. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 32 | `scripts/record_stage4.py:100` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 33 | `scripts/record_stage4.py:101` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 34 | `scripts/record_stage4.py:114` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 35 | `scripts/record_stage4.py:120` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 36 | `scripts/record_stage5.py:6` | B405 | LOW/HIGH | Import warning; associated parser hardened. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 37 | `scripts/record_stage5.py:84` | B314 | MEDIUM/HIGH | Real unnecessary XML parsing exposure; fixed. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 38 | `scripts/record_stage5.py:96` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 39 | `scripts/record_stage5.py:97` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 40 | `scripts/record_stage5.py:98` | B314 | MEDIUM/HIGH | Real unnecessary XML parsing exposure; fixed. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 41 | `scripts/record_stage5.py:100` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 42 | `scripts/record_stage5.py:102` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 43 | `scripts/record_stage5.py:111` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 44 | `scripts/record_stage5.py:119` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 45 | `scripts/record_stage5.py:129` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 46 | `scripts/record_stage6.py:6` | B405 | LOW/HIGH | Import warning; associated parser hardened. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 47 | `scripts/record_stage6.py:77` | B314 | MEDIUM/HIGH | Real unnecessary XML parsing exposure; fixed. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 48 | `scripts/record_stage6.py:78` | B314 | MEDIUM/HIGH | Real unnecessary XML parsing exposure; fixed. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 49 | `scripts/record_stage6.py:81` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 50 | `scripts/record_stage6.py:89` | B314 | MEDIUM/HIGH | Real unnecessary XML parsing exposure; fixed. Applied defusedxml 0.7.1 in the dev dependency group; no suppression. |
| 51 | `scripts/record_stage6.py:105` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 52 | `scripts/record_stage6.py:112` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 53 | `scripts/record_stage6.py:116` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 54 | `scripts/record_stage6.py:131` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 55 | `scripts/record_stage6.py:132` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 56 | `scripts/record_stage6.py:180` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 57 | `scripts/record_stage6.py:181` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 58 | `scripts/record_stage6.py:182` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 59 | `scripts/record_stage6.py:183` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 60 | `scripts/recovery_stage6.py:6` | B404 | LOW/HIGH | Import warning; no independent vulnerability; retained. Keep the import; review callers when commands or input sources change. |
| 61 | `scripts/recovery_stage6.py:23` | B607 | LOW/HIGH | Real conditional local PATH substitution risk; accepted low residual. Run only with a trusted Docker installation and PATH in the trusted local workspace. These legacy recovery scripts are not the published demo workflow. |
| 62 | `scripts/recovery_stage6.py:23` | B603 | LOW/HIGH | False positive for command injection in current call sites; retained. Keep shell=False and fixed argv; do not connect these wrappers to untrusted input. |
| 63 | `scripts/recovery_stage6.py:34` | B603 | LOW/HIGH | False positive for command injection in current call sites; retained. Keep shell=False and fixed argv; do not connect these wrappers to untrusted input. |
| 64 | `scripts/recovery_stage6.py:94` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 65 | `scripts/recovery_stage6.py:133` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 66 | `scripts/recovery_stage6.py:141` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 67 | `scripts/recovery_stage6.py:148` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 68 | `scripts/recovery_stage6.py:153` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 69 | `scripts/recovery_stage6.py:162` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 70 | `scripts/recovery_stage6.py:176` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 71 | `scripts/recovery_stage6.py:195` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 72 | `scripts/replay_stage6.py:30` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 73 | `scripts/stage3_manifest.py:51` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 74 | `scripts/stage4_support.py:31` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 75 | `scripts/stage4_support.py:33` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 76 | `scripts/stage4_support.py:107` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 77 | `scripts/stage5_support.py:36` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 78 | `scripts/stage5_support.py:70` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 79 | `scripts/stage5_support.py:72` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 80 | `scripts/stage6_benchmark.py:35` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 81 | `scripts/stage6_benchmark.py:44` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 82 | `scripts/stage6_benchmark.py:73` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 83 | `scripts/stage6_dataset.py:18` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 84 | `scripts/stage6_dataset.py:20` | B311 | LOW/HIGH | False positive for cryptographic use; retained. Keep deterministic data generation. Use secrets for credentials; historical dataset bytes remain unchanged. |
| 85 | `scripts/stage6_dataset.py:125` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 86 | `scripts/stage6_dataset.py:143` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 87 | `scripts/stage6_support.py:45` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 88 | `scripts/stage6_support.py:73` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 89 | `scripts/verify_aligned.py:46` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 90 | `scripts/verify_aligned.py:49` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 91 | `scripts/verify_baseline_repeat.py:33` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 92 | `scripts/verify_baseline_repeat.py:34` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 93 | `scripts/verify_baseline_repeat.py:59` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 94 | `scripts/verify_graph.py:82` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 95 | `scripts/verify_graph.py:87` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 96 | `scripts/verify_graph.py:98` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 97 | `scripts/verify_graph_runtime.py:18` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 98 | `scripts/verify_graph_runtime.py:44` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 99 | `scripts/verify_graph_runtime.py:45` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 100 | `scripts/verify_graph_runtime.py:47` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 101 | `scripts/verify_graph_runtime.py:48` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 102 | `scripts/verify_graph_runtime.py:50` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 103 | `scripts/verify_graph_runtime.py:51` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 104 | `scripts/verify_graph_runtime.py:62` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 105 | `scripts/verify_runtime.py:5` | B404 | LOW/HIGH | Import warning; no independent vulnerability; retained. Keep the import; review callers when commands or input sources change. |
| 106 | `scripts/verify_runtime.py:30` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 107 | `scripts/verify_runtime.py:39` | B607 | LOW/HIGH | Real conditional local PATH substitution risk; accepted low residual. Run only with a trusted Docker installation and PATH in the trusted local workspace. These legacy recovery scripts are not the published demo workflow. |
| 108 | `scripts/verify_runtime.py:39` | B603 | LOW/HIGH | False positive for command injection in current call sites; retained. Keep shell=False and fixed argv; do not connect these wrappers to untrusted input. |
| 109 | `scripts/verify_runtime.py:45` | B603 | LOW/HIGH | False positive for command injection in current call sites; retained. Keep shell=False and fixed argv; do not connect these wrappers to untrusted input. |
| 110 | `scripts/verify_stage5_runtime.py:7` | B404 | LOW/HIGH | Import warning; no independent vulnerability; retained. Keep the import; review callers when commands or input sources change. |
| 111 | `scripts/verify_stage5_runtime.py:26` | B607 | LOW/HIGH | Real conditional local PATH substitution risk; accepted low residual. Run only with a trusted Docker installation and PATH in the trusted local workspace. These legacy recovery scripts are not the published demo workflow. |
| 112 | `scripts/verify_stage5_runtime.py:26` | B603 | LOW/HIGH | False positive for command injection in current call sites; retained. Keep shell=False and fixed argv; do not connect these wrappers to untrusted input. |
| 113 | `scripts/verify_stage5_runtime.py:60` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 114 | `scripts/verify_stage5_runtime.py:95` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 115 | `scripts/verify_stage5_runtime.py:96` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 116 | `scripts/verify_stage5_runtime.py:98` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 117 | `scripts/verify_stage5_runtime.py:100` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 118 | `scripts/verify_stage5_runtime.py:125` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 119 | `scripts/verify_stage5_runtime.py:134` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 120 | `scripts/verify_stage5_runtime.py:172` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 121 | `scripts/verify_vector_index.py:31` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 122 | `scripts/verify_vector_index.py:33` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 123 | `scripts/verify_vector_index.py:40` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 124 | `scripts/verify_vector_runtime.py:34` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 125 | `scripts/verify_vector_runtime.py:35` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 126 | `scripts/verify_vector_runtime.py:36` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 127 | `scripts/verify_vector_runtime.py:44` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 128 | `scripts/verify_vector_runtime.py:47` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 129 | `scripts/verify_vector_runtime.py:54` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 130 | `scripts/verify_vector_runtime.py:64` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
| 131 | `scripts/verify_vector_runtime.py:66` | B101 | LOW/HIGH | Real verification/preservation issue under python -O; fixed. Applied explicit conditional exception; no suppression. |
