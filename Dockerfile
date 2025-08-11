FROM ubuntu:20.04

RUN apt update && apt install -y wget python3-pip

RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.focal_amd64.deb \
    && apt install -y ./wkhtmltox_0.12.6-1.focal_amd64.deb

RUN pip3 install pdfkit flask requests schedule gunicorn

COPY app/ app/

WORKDIR /app

EXPOSE 80 443

CMD ["gunicorn", "--bind", "0.0.0.0:80", "main:app"]
