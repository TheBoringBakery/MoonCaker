FROM tiangolo/meinheld-gunicorn-flask:python3.7

COPY ./mooncaker /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt