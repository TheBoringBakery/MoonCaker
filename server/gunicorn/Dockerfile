FROM python:3.7-alpine3.8

RUN apk add --no-cache --virtual .build-deps gcc libc-dev \
    && pip install gunicorn

ADD . /

RUN chmod +x /start.sh

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000 587

ENV PYTHONPATH=/mooncaker

CMD [ "/start.sh" ]