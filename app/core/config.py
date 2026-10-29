from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", frozen=True, hide_input_in_errors=True
    )

    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1024, le=65535)
    neo4j_uri: str = "bolt://127.0.0.1:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr
    neo4j_database: str = "neo4j"
    neo4j_connection_timeout: float = Field(default=3, gt=0, le=30)
    neo4j_query_timeout: float = Field(default=5, gt=0, le=60)
    neo4j_import_timeout: float = Field(default=60, gt=0, le=300)
    neo4j_pool_size: int = Field(default=10, ge=1, le=100)
    neo4j_write_retry_time: float = Field(default=3, ge=0, le=30)
    ingestion_max_bytes: int = Field(default=65536, ge=1, le=1048576)
    ingestion_chunk_size: int = Field(default=600, ge=32, le=16000)
    ingestion_chunk_overlap: int = Field(default=80, ge=0, le=15999)
    ingestion_batch_size: int = Field(default=20, ge=1, le=100)
    ingestion_lease_seconds: int = Field(default=300, ge=30, le=3600)
    embedding_startup_timeout: float = Field(default=180, ge=1, le=300)
    embedding_inference_timeout: float = Field(default=30, ge=1, le=120)
    vector_corpus: str = Field(default="fictional-v1", pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    vector_query_timeout: float = Field(default=20, gt=0, le=60)
    graph_query_timeout: float = Field(default=10, gt=0, le=30)
    graph_request_timeout: float = Field(default=20, ge=1, le=60)
    graph_max_candidates: int = Field(default=128, ge=1, le=256)
    graph_max_answers: int = Field(default=10, ge=1, le=20)
    stage5_neo4j_uri: str = "bolt://127.0.0.1:17688"
    hybrid_request_timeout: float = Field(default=60, ge=1, le=120)

    @field_validator("neo4j_password")
    @classmethod
    def strong_local_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if (
            len(password) < 12
            or password.startswith("replace-")
            or any(c.isspace() or c in "/$" for c in password)
        ):
            raise ValueError("Use a local password of 12+ characters without whitespace, / or $")
        return value

    @field_validator("neo4j_uri", "stage5_neo4j_uri")
    @classmethod
    def valid_uri(cls, value: str) -> str:
        from urllib.parse import urlsplit

        uri = urlsplit(value)
        if uri.scheme not in {"bolt", "bolt+s", "neo4j", "neo4j+s"} or not uri.hostname:
            raise ValueError("Invalid Neo4j URI")
        if uri.username or uri.password or uri.query or uri.fragment:
            raise ValueError("Keep credentials separate from the Neo4j URI")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
