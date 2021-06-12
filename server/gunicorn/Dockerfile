FROM python:3.7-alpine3.8

RUN apk add --no-cache --virtual .build-deps gcc libc-dev \
    && pip install gunicorn

ADD . /

RUN chmod +x /start.sh

RUN chmod +x /install_db.sh

RUN /install_db.sh

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000 465

ENV PYTHONPATH=/mooncaker

CMD [ "/start.sh" ]