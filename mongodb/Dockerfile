FROM python:3.7-alpine3.8

ADD install_db.sh /install_db.sh

RUN chmod +x /install_db.sh

RUN /install_db.sh

EXPOSE 27017

CMD [ "mongod", "--dbpath", "/DataCaker/data", "--bind_ip", "0.0.0.0" ]