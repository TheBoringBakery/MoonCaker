FROM galatolo/gunicorn-nginx:latest

ADD . /mooncaker
ADD ./.ssl /.ssl


ENV gunicorn_config_file="/mooncaker/gunicorn.conf.py"
ENV use_tls="true"
ENV domain="theboringbakery.com"
ENV MODULE_NAME="mooncaker"
ENV PYTHONPATH="/mooncaker"

RUN pip install --no-cache-dir -r /mooncaker/requirements.txt
RUN chmod +x /mooncaker/install_riot_watcher.sh
RUN /mooncaker/install_riot_watcher.sh
