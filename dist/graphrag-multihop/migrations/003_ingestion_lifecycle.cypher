CREATE CONSTRAINT ingestion_source_id IF NOT EXISTS FOR (n:IngestionSource) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT ingestion_run_id IF NOT EXISTS FOR (n:Ingestion) REQUIRE n.id IS UNIQUE;
CREATE INDEX ingestion_source_lookup IF NOT EXISTS FOR (n:Ingestion) ON (n.source_id);
CREATE INDEX ingestion_status_lookup IF NOT EXISTS FOR (n:Ingestion) ON (n.status);
CREATE INDEX document_source_lookup IF NOT EXISTS FOR (n:Document) ON (n.source_id);
