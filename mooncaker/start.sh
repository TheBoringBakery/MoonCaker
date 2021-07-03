#! /usr/bin/env sh
set -e

# Start Gunicorn
exec gunicorn -c "/mooncaker/gunicorn.conf.py"
