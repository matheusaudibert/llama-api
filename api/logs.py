"""Logging setup. Lines carry key=value fields (or JSON with LOG_FORMAT=json) and the request id.

Never log tokens, session ids, emails or display names: use session_ref() to correlate a session.
"""
import contextvars
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def fields(**values) -> dict:
    """extra= for a log call: logger.info("Login completed", extra=fields(session=ref))."""
    return {"fields": values}


def session_ref(session_id: str) -> str:
    """Short, stable reference for a session id that is safe to log."""
    return hashlib.sha256(session_id.encode()).hexdigest()[:8]


def _logger_name(record: logging.LogRecord) -> str:
    # uvicorn's normal startup lines come from a logger called "uvicorn.error"
    return "uvicorn" if record.name.startswith("uvicorn") else record.name


def _value(v) -> str:
    text = str(v)
    return json.dumps(text) if (" " in text or "=" in text or not text) else text


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        time = datetime.fromtimestamp(record.created, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        line = f"{time} {record.levelname:<7} {_logger_name(record):<13} [{request_id.get()}] {record.getMessage()}"
        extra = getattr(record, "fields", None)
        if extra:
            line += " " + " ".join(f"{k}={_value(v)}" for k, v in extra.items() if v is not None)
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": _logger_name(record),
            "request_id": request_id.get(),
            "message": record.getMessage(),
            **{k: v for k, v in (getattr(record, "fields", None) or {}).items() if v is not None},
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def setup_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if os.environ.get("LOG_FORMAT", "text").lower() == "json" else TextFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    # DEBUG only for our own loggers: the libraries are too chatty at that level
    root.setLevel("INFO" if level == "DEBUG" else level)
    logging.getLogger("api").setLevel(level)

    # uvicorn logs startup and errors through our handler; its access log is replaced by the
    # request middleware, which logs the route template instead of the path with the session id
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.propagate = False
    logging.getLogger("uvicorn.access").disabled = True
