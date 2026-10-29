# Graph-only error analysis

The registry, extraction, graph snapshot, Stage 3 data and grading rules are frozen. These results include upstream coverage failures; no gold-derived edges were added.

Citation/validation percentages are N/A when zero evidence was returned.

Causes across all abstentions: {'missing_extraction_fact': 121, 'ambiguous_entity_resolution': 1}

| ID | Split | Hops | Expected | Actual | Cause | Origin | Reason |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| s01-q01 | calibration | 1 | Boreal; Boreal Annex | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s01-q02 | calibration | 1 | Orion Orchard | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s01-q03 | calibration | 1 | CobaltDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s01-q04 | calibration | 2 | CobaltDB; Firebird | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s01-q05 | calibration | 2 | Orion Orchard | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s01-q06 | calibration | 2 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s01-q07 | calibration | 3 | AWS; Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s01-q08 | calibration | 3 | AWS; Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s01-u1 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s01-u2 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s02-q01 | calibration | 1 | Saffron | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s02-q02 | calibration | 1 | Kestrel Grove | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s02-q03 | calibration | 1 | MariaDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s02-q04 | calibration | 2 | MariaDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s02-q05 | calibration | 2 | Kestrel Grove | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s02-q06 | calibration | 2 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s02-q07 | calibration | 3 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s02-q08 | calibration | 3 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s02-u1 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s02-u2 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s03-q01 | calibration | 1 | Boreal East | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s03-q02 | calibration | 1 | Mica Harbor | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s03-q03 | calibration | 1 | Memcached | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s03-q04 | calibration | 2 | Memcached | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s03-q05 | calibration | 2 | Mica Harbor | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s03-q06 | calibration | 2 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s03-q07 | calibration | 3 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s03-q08 | calibration | 3 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s03-u1 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s03-u2 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s04-q01 | calibration | 1 | Juniper | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s04-q02 | calibration | 1 | Sable Meadow | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s04-q03 | calibration | 1 | ClickHouse | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s04-q04 | calibration | 2 | ClickHouse | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s04-q05 | calibration | 2 | Sable Meadow | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s04-q06 | calibration | 2 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s04-q07 | calibration | 3 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s04-q08 | calibration | 3 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s04-u1 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s04-u2 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s05-q01 | calibration | 1 | Topaz | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s05-q02 | calibration | 1 | Copper Nest | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s05-q03 | calibration | 1 | Cassandra | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s05-q04 | calibration | 2 | Cassandra | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s05-q05 | calibration | 2 | Copper Nest | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s05-q06 | calibration | 2 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s05-q07 | calibration | 3 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s05-q08 | calibration | 3 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s05-u1 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s05-u2 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s06-q01 | calibration | 1 | Willow | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s06-q02 | calibration | 1 | Lantern Vale | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s06-q03 | calibration | 1 | SQLite | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s06-q04 | calibration | 2 | SQLite | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s06-q05 | calibration | 2 | Lantern Vale | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s06-q06 | calibration | 2 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s06-q07 | calibration | 3 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s06-q08 | calibration | 3 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s06-u1 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s06-u2 | calibration | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s07-q01 | held_out | 1 | Cedar Bridge | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s07-q02 | held_out | 1 | Pebble Arc | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s07-q03 | held_out | 1 | OceanBase | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s07-q04 | held_out | 2 | OceanBase | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s07-q05 | held_out | 2 | Pebble Arc | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s07-q06 | held_out | 2 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s07-q07 | held_out | 3 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s07-q08 | held_out | 3 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s07-u1 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s07-u2 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s08-q01 | held_out | 1 | Indigo | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s08-q02 | held_out | 1 | Silver Loom | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s08-q03 | held_out | 1 | ScyllaDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s08-q04 | held_out | 2 | ScyllaDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s08-q05 | held_out | 2 | Silver Loom | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s08-q06 | held_out | 2 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s08-q07 | held_out | 3 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s08-q08 | held_out | 3 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s08-u1 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s08-u2 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s09-q01 | held_out | 1 | Cedar Bridge West | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s09-q02 | held_out | 1 | Amber Quay | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s09-q03 | held_out | 1 | ArangoDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s09-q04 | held_out | 2 | ArangoDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s09-q05 | held_out | 2 | Amber Quay | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s09-q06 | held_out | 2 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s09-q07 | held_out | 3 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s09-q08 | held_out | 3 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s09-u1 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s09-u2 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s10-q01 | held_out | 1 | Marigold | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s10-q02 | held_out | 1 | Birch Canvas | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s10-q03 | held_out | 1 | RocksDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s10-q04 | held_out | 2 | RocksDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s10-q05 | held_out | 2 | Birch Canvas | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s10-q06 | held_out | 2 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s10-q07 | held_out | 3 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s10-q08 | held_out | 3 | GCP | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s10-u1 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s10-u2 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s11-q01 | held_out | 1 | Quartz | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s11-q02 | held_out | 1 | Aster Bay | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s11-q03 | held_out | 1 | HBase | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s11-q04 | held_out | 2 | HBase | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s11-q05 | held_out | 2 | Aster Bay | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s11-q06 | held_out | 2 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s11-q07 | held_out | 3 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s11-q08 | held_out | 3 | AWS | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s11-u1 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s11-u2 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s12-q01 | held_out | 1 | Quartz South | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s12-q02 | held_out | 1 | Elm Crest | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s12-q03 | held_out | 1 | TiDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s12-q04 | held_out | 2 | TiDB | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s12-q05 | held_out | 2 | Elm Crest | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s12-q06 | held_out | 2 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s12-q07 | held_out | 3 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s12-q08 | held_out | 3 | Azure | None | missing_extraction_fact | stage2_identity_coverage | entity_not_found |
| s12-u1 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| s12-u2 | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
| calibration-ambiguous | calibration | 0 | None | None | ambiguous_entity_resolution | registry_identity | entity_ambiguous |
| held_out-ambiguous | held_out | 0 | None | None | missing_extraction_fact | expected_missing_or_unregistered_entity | entity_not_found |
