FROM nginx:1.19-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY .ssl .ssl

COPY nginx.conf /etc/nginx/conf.d