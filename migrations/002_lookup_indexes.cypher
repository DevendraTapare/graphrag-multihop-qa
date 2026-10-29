CREATE INDEX entity_name_scope IF NOT EXISTS FOR (n:GraphNode) ON (n.normalized_name, n.scope);
CREATE INDEX fixture_nodes IF NOT EXISTS FOR (n:GraphNode) ON (n.fixture_id);
CREATE INDEX chunk_document IF NOT EXISTS FOR (n:Chunk) ON (n.document_id);
