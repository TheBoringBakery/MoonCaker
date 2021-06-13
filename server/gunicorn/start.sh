#! /usr/bin/env sh
set -e

# Start Gunicorn
exec gunicorn -c "gunicorn.conf.py"