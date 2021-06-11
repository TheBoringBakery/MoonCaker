#! /usr/bin/env sh
set -e

# Start Gunicorn
exec mongod --dbpath /DataCaker/data &
sleep 10
exec gunicorn -k egg:meinheld#gunicorn_worker -c "gunicorn.conf.py"