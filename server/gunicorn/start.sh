#! /usr/bin/env sh
set -e

# Start Gunicorn
exec mongod --dbpath /DataCaker/data &
sleep 10
exec gunicorn -c "gunicorn.conf.py" --certfile ".ssl/cert.pem" --keyfile ".ssl/private.pem"