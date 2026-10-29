import json
import logging
import re
from contextvars import ContextVar
from datetime import UTC, datetime

request_id: ContextVar[str] = ContextVar("request_id", default="-")
_secrets: tuple[str, ...] = ()


def redact(value: str) -> str:
    for secret in _secrets:
        value = value.replace(secret, "[REDACTED]")
    value = re.sub(r"(?i)(password|token|authorization)\s*[:=]\s*\S+", r"\1=[REDACTED]", value)
    return re.sub(r"(\w+://)[^\s/@]+:[^\s/@]+@", r"\1[REDACTED]@", value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": redact(record.getMessage()),
                "request_id": request_id.get(),
            }
        )


def configure_logging(password: str) -> None:
    global _secrets
    _secrets = (password,)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
