from __future__ import print_function

import json
import multiprocessing
import os

workers_per_core_str = os.getenv("WORKERS_PER_CORE", "2")
web_concurrency_str = os.getenv("WEB_CONCURRENCY", None)
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "5000")
bind = f'{host}:{port}' #[f'{host}:443', f'{host}:80']

cores = multiprocessing.cpu_count()
workers_per_core = float(workers_per_core_str)
default_web_concurrency = workers_per_core * cores
if web_concurrency_str:
    web_concurrency = int(web_concurrency_str)
    assert web_concurrency > 0
else:
    web_concurrency = int(default_web_concurrency)

# Gunicorn config variables
workers = web_concurrency
keepalive = 120
errorlog = "-"
accesslog = "-"
loglevel = 'debug'

# For debugging and testing
log_data = {
    "workers": workers,
    # Additional, non-gunicorn variables
    "workers_per_core": workers_per_core,
    "bind": bind,
}
print(json.dumps(log_data))

preload_app = True
wsgi_app = "mooncaker:app"

# worker_class = "egg:meinheld#gunicorn_worker"
