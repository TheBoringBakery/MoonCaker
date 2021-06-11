FROM python:3.7-alpine3.8

RUN apk add --no-cache --virtual .build-deps gcc libc-dev \
    && pip install meinheld gunicorn

ADD . /

RUN chmod +x /start.sh

RUN chmod +x /install_db.sh

RUN /install_db.sh

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

EXPOSE 465

# WORKDIR /mooncaker

ENV PYTHONPATH=/mooncaker


CMD [ "/start.sh" ]

# FROM tiangolo/meinheld-gunicorn-flask:python3.7

# COPY ./mooncaker /app

# COPY requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt