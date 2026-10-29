CREATE CONSTRAINT chunk_embedding_id IF NOT EXISTS FOR (n:ChunkEmbedding) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT vector_build_id IF NOT EXISTS FOR (n:VectorBuild) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT vector_corpus_id IF NOT EXISTS FOR (n:VectorCorpus) REQUIRE n.id IS UNIQUE;
CREATE VECTOR INDEX chunk_minilm_cosine IF NOT EXISTS FOR (n:ChunkEmbedding) ON (n.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};
