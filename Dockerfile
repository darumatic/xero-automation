# Dockerfile
FROM ubuntu:18.04
ENV DEBIAN_FRONTEND noninteractive
RUN apt update && apt-get install -y build-essential libssl-dev libffi-dev wkhtmltopdf xfonts-75dpi python3.7 python-pip wget git python3-setuptools

# Install wkhtmltopdf to support headless
RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.bionic_amd64.deb -P /tmp
RUN dpkg -i /tmp/wkhtmltox_0.12.6-1.bionic_amd64.deb

# Create app directory
RUN mkdir -p /opt/xero_automation
COPY . /opt/xero_automation
RUN ls -la /opt/xero_automation

WORKDIR /opt/xero_automation
# Install app dependencies
RUN python3 setup.py install
