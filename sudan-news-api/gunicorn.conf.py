# Gunicorn configuration for production deployment

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Logging
loglevel = "info"
accesslog = "../../../shared/logs/access.log"
errorlog = "../../../shared/logs/error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "sudan-news-api"

# Server mechanics
daemon = False
pidfile = "../../../shared/logs/gunicorn.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# SSL (uncomment and configure for HTTPS)
# keyfile = "/path/to/ssl/private.key"
# certfile = "/path/to/ssl/certificate.crt"

# Application
wsgi_module = "src.app:app"
pythonpath = "."

# Development overrides (uncomment for dev)
# workers = 1
# reload = True
# loglevel = "debug"
