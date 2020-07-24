# Dockerfile
FROM python:3.7-alpine AS base

FROM base AS builder
RUN mkdir /install
WORKDIR /install
COPY requirements.txt /requirements.txt
RUN apk add --no-cache --update \
    libffi-dev \
    openssl-dev \
    readline-dev \
    build-base

RUN pip3 install --install-option="--prefix=/install" -r /requirements.txt

FROM base
COPY --from=builder /install /usr/local
COPY ["xero_client.py", "xero_report.py", "report.html", "/app/"]
WORKDIR /app
RUN apk add --no-cache \
    libgcc libstdc++ libx11 glib libxrender libxext libintl \
    ttf-dejavu ttf-droid ttf-freefont ttf-liberation ttf-ubuntu-font-family wkhtmltopdf
