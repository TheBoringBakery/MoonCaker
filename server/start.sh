#! /usr/bin/env sh
set -e

# Start Gunicorn
exec gunicorn -k egg:meinheld#gunicorn_worker -c "gunicorn.conf.py"