"""Gunicorn configuration for production.

HORIZONTAL SCALING NOTE:
When running multiple workers (workers > 1), only ONE worker should run the scheduler.
Set SCHEDULER_ENABLED=false for non-primary workers via environment variables or
use post_worker_init hook to enable scheduler only in first worker:

    def post_worker_init(worker):
        # Enable scheduler only for first worker
        import os
        if worker.age == 0:  # First worker
            os.environ["SCHEDULER_ENABLED"] = "true"
        else:
            os.environ["SCHEDULER_ENABLED"] = "false"
"""
import multiprocessing
import os

# Import settings - but handle case where app may not be importable
try:
    from app.config import get_settings
    _settings = get_settings()
    _host = _settings.server_host
    _port = _settings.server_port
    _workers = _settings.server_workers or (multiprocessing.cpu_count() * 2 + 1)
    _log_level = _settings.log_level.lower()
except Exception:
    _host = os.getenv("SERVER_HOST", "0.0.0.0")
    _port = os.getenv("SERVER_PORT", "8000")
    _workers = int(os.getenv("SERVER_WORKERS", multiprocessing.cpu_count() * 2 + 1))
    _log_level = os.getenv("LOG_LEVEL", "info").lower()

# Server socket
bind = f"{_host}:{_port}"

# Worker processes
workers = _workers
worker_class = "uvicorn.workers.UvicornWorker"
worker_tmp_dir = "/dev/shm"

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"  # stdout (container-friendly)
errorlog = "-"   # stderr (container-friendly)
loglevel = _log_level

# Access log format - includes response time and user agent
# Format: client_ip - user timestamp "request" status bytes "referrer" "user_agent" response_time_us
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Security
limit_request_line = 8190
limit_request_fields = 100
