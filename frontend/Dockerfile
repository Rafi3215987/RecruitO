FROM nginx:alpine

COPY frontend/ /usr/share/nginx/html/
COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY background2.png /usr/share/nginx/html/background2.png

EXPOSE 80
