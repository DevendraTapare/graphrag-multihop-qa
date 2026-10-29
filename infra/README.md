# Local infrastructure

The authoritative Compose file is `../compose.yaml`, beside `.env`. Run Compose from the repository root so its environment file and project name resolve consistently. It uses Neo4j Community 5.26.32, a named data volume, a lightweight HTTP health check using Bash builtins, and loopback-only host ports. The API readiness route verifies actual authenticated query execution.

The health check starts no Java process. Repeated timed-out `cypher-shell` probes previously left orphan JVMs on this machine; recreating this project container cleared them while preserving the named data volume. A 60-second stop grace period allows database shutdown to finish.

The Neo4j username is `neo4j` for a newly initialized container. `NEO4J_AUTH` only sets the initial password for an empty volume. Do not disable authentication or publish host ports to all interfaces. Browser and Bolt host ports are configurable; see the main README.

No cloud service, deployment manifest, public database binding, or paid API is part of this stage. `docker compose down` preserves the data volume. Fixture reset is implemented as an explicitly confirmed, development-only CLI action that preserves unrelated data and schema.
