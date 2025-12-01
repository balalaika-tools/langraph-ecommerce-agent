import logging
import json
import os
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from queue import Queue
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path
import httpx
import sys
from typing import Optional, Union, ClassVar

class CorrelationCtx:
    _cid: ClassVar[ContextVar[Optional[str]]] = ContextVar("correlation_id", default=None)

    @classmethod
    def get(cls) -> Optional[str]:
        return cls._cid.get()

    @classmethod
    def set(cls, cid: Optional[str]):
        return cls._cid.set(cid)

    @classmethod
    def reset(cls, token):
        cls._cid.reset(token)

    @classmethod
    @contextmanager
    def use(cls, cid: Optional[str]):
        token = cls.set(cid)
        try:
            yield
        finally:
            cls.reset(token)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Attach correlation id to the log record.
        """
        if not getattr(record, "correlation_id", None):
            record.correlation_id = CorrelationCtx.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def _make_json_serializable(self, obj):
        from datetime import datetime, date
        from uuid import UUID

        if isinstance(obj, (UUID,)):
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, (set, frozenset)):
            return list(obj)
        elif isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, "__dict__"):
            try:
                return str(obj)
            except Exception:
                return repr(obj)
        return obj

    def _serialize_value(self, value):
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        else:
            return self._make_json_serializable(value)

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
            "rid": getattr(record, "correlation_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "stack_info",
                "exc_info", "exc_text", "correlation_id", "asctime"
            }:
                try:
                    data[key] = self._serialize_value(value)
                except Exception:
                    data[key] = str(value)
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


class WebhookHandler(logging.Handler):
    def __init__(self, webhook_url: str, timeout: float = 5.0, level=logging.ERROR):
        super().__init__(level)
        self.webhook_url = webhook_url
        self.timeout = timeout

    def emit(self, record: logging.LogRecord):
        try:
            payload = json.loads(JsonFormatter().format(record))
            with httpx.Client(timeout=self.timeout) as client:
                client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
        except Exception:
            pass


def configure_logging(
    *,
    log_file: Optional[Union[str, Path]] = None,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    console_output: bool = True,
    json_output: bool = True,
    logger_name: str = "gLogger",
    webhook_url: Optional[str] = None,
    webhook_timeout: float = 5.0,
) -> logging.Logger:
    # Determine environment
    env = os.getenv("APP_ENVIRONMENT", "").strip().lower()
    # Default level: DEBUG for non-prod, ERROR for prod
    if env == "prod":
        level = logging.ERROR
    else:
        level = logging.DEBUG

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.handlers.clear()
    logger.filters.clear()

    cid_filter = CorrelationIdFilter()

    log_queue = Queue()
    queue_handler = QueueHandler(log_queue)
    queue_handler.addFilter(cid_filter)
    logger.addHandler(queue_handler)

    handlers = []
    if console_output:
        ch = logging.StreamHandler(sys.stdout)
        handlers.append(ch)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_file, maxBytes=max_file_size, backupCount=backup_count, encoding="utf-8"
        )
        handlers.append(fh)
    if webhook_url:
        wh = WebhookHandler(webhook_url=webhook_url, timeout=webhook_timeout, level=logging.ERROR)
        handlers.append(wh)

    formatter = JsonFormatter() if json_output else logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s [rid=%(correlation_id)s] - %(message)s - %(pathname)s:%(lineno)d",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    for h in handlers:
        h.setFormatter(formatter)
        h.addFilter(cid_filter)

    listener = QueueListener(log_queue, *handlers, respect_handler_level=True)
    listener.start()
    logger._queue_listener = listener
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    logger_name = name if name else ""
    return logging.getLogger(logger_name)
