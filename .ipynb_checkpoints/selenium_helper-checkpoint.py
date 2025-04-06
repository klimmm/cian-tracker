import os
import multiprocessing

# Bind address
bind = f"0.0.0.0:{os.getenv('PORT', '8050')}"

# Number of worker processes
workers = os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1)

# Timeout
timeout = 120

# Access log - STDOUT
accesslog = "-"

# Error log - STDERR
errorlog = "-"

# Log level
loglevel = "info"

# Process name
proc_name = "cian_dashboard"

# Preload application
preload_app = True

# Worker class
worker_class = "sync"

# Max requests per worker
max_requests = 1000
max_requests_jitter = 50

# Disable keepalive
keepalive = 5