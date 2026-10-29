# Stage 4 file inventory

Only the seven existing integration files below changed. All other frozen Stage 3 files remain byte-identical. No dependency or schema change was needed.

## Changed existing files

| File | SHA-256 |
| --- | --- |
| `.env.example` | `9eb9fa2d00fc87bff1171c5582be5e61f52b429a2f3b56bae31b059e56ac8243` |
| `README.md` | `79346659162c7851cd781878e98c5524ed0a422a6c56d0db60471df9453c071c` |
| `app/core/config.py` | `52822c1e7beef55e36b1ef98aa1889ea249952f5225e3bb5efb8f726694c8ad6` |
| `app/main.py` | `be2983fa31c3992fd27316abd613917dc96430e051369d4ccc52567a2bca8e77` |
| `docs/PROJECT_ROADMAP.md` | `8943208fd49dfc425229863bfc8d589cf90315e599d382c12142d888e8f35fce` |
| `reports/README.md` | `6d42191d9e228d32da418af99f651cc2a8b5f5fee39cd348176f61a373be5ee2` |
| `tests/unit/test_api.py` | `d5fb8561c5acc7034b4bc21538144f63cf910ac360429c6e1b898a48231dbbe7` |

## New files

| File | SHA-256 |
| --- | --- |
| `app/api/graph_rag.py` | `12ea090fb177c92e306c3dd2ef756e35e38f5d7c9f09ec3704b190c6f6dd026d` |
| `app/evaluation/graph.py` | `068dec56dd6fdf8875825b8c91b69ee33f720e1ab2cf92adc1daea85eef057d9` |
| `app/graph_rag/__init__.py` | `97b12edd5a8508a6aef44d98d994cb53aef9a6184c23c02ef438fc9cae123507` |
| `app/graph_rag/interpretation.py` | `4c2d086f8877ba49008b179188f86d246f9f7687bed30f448a790c24a0603ff0` |
| `app/graph_rag/linking.py` | `67afc660a7c044d1e0976a871de30c59e1aad6e4d98ef40efa20c7791fb87e14` |
| `app/graph_rag/models.py` | `dcb7db12abf92ff0d397e38bb4d6897b9c1d31f1ba9576cddc88524e9252f419` |
| `app/graph_rag/provenance.py` | `a0d7008173b46ff3c5e9c43846e843085c074a4c79d57411a25fb0a7c9df7fa2` |
| `app/graph_rag/repository.py` | `bbe96af64c50e8a5fa924e867d0e0366ab3b34453b872fb546e00dc567b15fc4` |
| `app/graph_rag/service.py` | `ca32e07084417438bcff37b6957e4846a1573b0b542f6dd4aa84e2bd55c0ebb3` |
| `data/runtime/graph_corpus_v1.json` | `10f5e6e04a21f6df0f11c5af4d2a15804e3597f4c53f109dfc8fc64c8b947320` |
| `docs/ENTITY_LINKING.md` | `4d12720b98f719c702f65752ad9b3681cd469f1db636c811305676fb3af7fdc0` |
| `docs/GRAPH_EVALUATION.md` | `d7d9d49e77b0ec7ae0a34da6c495ce2b9802257fe779fe31bf9b2ca0404ce904` |
| `docs/GRAPH_RETRIEVAL_ARCHITECTURE.md` | `20974cf17add9b3c3190103fc2a4c2ff9da30fe3a87f5a00b8c2870f33d154cb` |
| `docs/GRAPH_SECURITY_TESTS.md` | `eefd48e1745a5f005c733d9bf3855deacbc5d1c33f4681ace36a7ca1dc9d6800` |
| `docs/MULTIHOP_REASONING.md` | `06ad2fcc9862cd20b51bbebd5abcfd1ff5562284b652ab8623085fc3b5d3bcfe` |
| `docs/STAGE4_PLAN.md` | `b2b88e6551ba817d67f09a73049442ad350329470b2b26f2e994559163620030` |
| `docs/STAGE4_REPORT.md` | `6ee7300b495a2afd81b9f674e0668cffc751b787f8d854e66952462b769d4475` |
| `reports/stage4/baseline_freeze.json` | `7c317b3ba1e3f323f1dda9aff7f235c98dcf7f3ff2b08ed22c194b0d9bcd10e1` |
| `reports/stage4/comparison.json` | `175dd0efd7f7c29acba664299d131d5dfc080eb300026c995952b70a133a7c72` |
| `reports/stage4/determinism.json` | `d691bc6f65fbea8cd260ce360cc436cdb93059ba0732fbc815208b4fcb970559` |
| `reports/stage4/error_analysis.md` | `60ac924904ed023169bfbafdee83df07261db84823a08c43c06ebe18e1cc9415` |
| `reports/stage4/frozen_stage3.zip` | `7c343d96c0406db6b56989733a4f603b15078c0d529895e0b549158c3c760c4d` |
| `reports/stage4/graph_metrics.csv` | `bb67182ad5602c4e2d96b38e88b3cee11bb35fc244b696b5447d3472014fa074` |
| `reports/stage4/graph_metrics.json` | `231cd3819a224a7ee609657cd43b7bd886b817149e7d5f489ff0d86935c84bad` |
| `reports/stage4/graph_snapshot.json` | `449ea1c1703fcecf7a75f2445102d9de19a5b7c8624fd41985675ce154a57a63` |
| `reports/stage4/operational_verification.json` | `75dc220b888167e0a2fc97a4970d6d0d271bcc920c1c97eabf75b7d3f397094a` |
| `reports/stage4/retrieval_code_freeze.json` | `b2bfaf0a1d1a252ae080a22a7bdebbb09872bd9c6df6a4f655ff9064eb7aaaaa` |
| `reports/stage4/runtime_verification.json` | `9391aaceae0d4ac9be7a40083159256149f3425d2a0d6ff2786f8977b75d5822` |
| `reports/stage4/source_coverage.json` | `20e5cfd177856efd276c273d2621f2d9b155cf191ed317a2cbc85893efde1206` |
| `reports/stage4/test_results.json` | `eb4869ed47edd29046f37b8a38b1baef3400fda1d89c4ecf087e67f474052c80` |
| `reports/stage4/vector_recheck.json` | `abce0d0348e228820b1bbef77e4c7d696be20789d3b069bdc748f477ba77fdae` |
| `scripts/audit_graph_coverage.py` | `ef197d77c9cf0a5a669649aecf4fc234cde5f239d41dbf17164499efba1e9bc1` |
| `scripts/compare_stage4.py` | `365ef3eebfa0fb6e857691fbd428ed47ed51295beaa7b59d8b83916f6dbbaf53` |
| `scripts/evaluate_graph.py` | `782c5733457b852c79599566bb52fbd693912d0266277632a883b78520b00734` |
| `scripts/graph_rag.py` | `7365b876704f8552082aca0d6368257d0b8d5683199ccde6bd74a914fd7807a8` |
| `scripts/record_stage4.py` | `d6a8c4680a0c34ea1049ded520b1ef46c8b22c8ba8a24a27992b558ffd4fa2f0` |
| `scripts/stage4_support.py` | `593894d5c003f646fa6bb5d8802960eeb430f62f935ae74c26e09061f9c8618d` |
| `scripts/verify_graph.py` | `e0d8222f0175ffe003bba65888dade418e662dbb6dd47406505a4239327b0fed` |
| `scripts/verify_graph_runtime.py` | `c3aaf86b856fd260fa4c8aa2bfe7cb6a067c0c4fa44ba6cb51d0116e4a24104a` |
| `tests/integration/test_graph_rag.py` | `325fa5552b8fe1b88d2417ed463c510c250038168b5cc8309b9d019d9f272fad` |
| `tests/unit/test_graph_api.py` | `e6c29d06ee690473f79836234c25cb0f1f6237beafc60cd8bf94fefe7ca7b906` |
| `tests/unit/test_graph_evaluation.py` | `d6d0e1bf415a3265e52042ce955293782f1519303ccfdacdfe75fef96b7805dc` |
| `tests/unit/test_graph_rag.py` | `00afb889f2a0440d507947c52f1a15c3a1b105bd4d47f80c85e2c4b50b4f7c30` |
| `reports/stage4/FILE_MANIFEST.md` | Self; omitted to avoid recursive hashing |

7 changed existing files; 44 new shareable files.

Local .env, environments, caches, logs and JUnit XML are excluded. The local JUnit evidence is reports/stage4-tests.xml.
