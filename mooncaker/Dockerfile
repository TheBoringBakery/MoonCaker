FROM galatolo/gunicorn-nginx:python3.7-alpine

ADD . /mooncaker
ADD ./.ssl /.ssl


ENV GUNICORN_CONFIG_FILE="/mooncaker/gunicorn.conf.py"
ENV USE_TLS="true"
ENV DOMAIN="theboringbakery.com"
ENV MODULE_NAME="flask_app"
ENV PYTHONPATH="/mooncaker"

RUN pip install --no-cache-dir -r /mooncaker/requirements.txt
RUN chmod +x /mooncaker/install_riot_watcher.sh
RUN /mooncaker/install_riot_watcher.sh
RUN apk add mongodb-tools
