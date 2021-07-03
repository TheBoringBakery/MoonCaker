FROM python:3.7-alpine3.8

RUN apk add --no-cache --virtual .build-deps gcc libc-dev \
    && pip install gunicorn

ADD . /mooncaker

RUN chmod +x /mooncaker/start.sh

RUN pip install --no-cache-dir -r /mooncaker/requirements.txt

RUN chmod +x /mooncaker/install_riot_watcher.sh

RUN /mooncaker/install_riot_watcher.sh

EXPOSE 5000 587

ENV PYTHONPATH=/mooncaker

CMD [ "/mooncaker/start.sh" ]
