# Dockerfile
FROM ubuntu:18.04
RUN apt update && apt-get install -y build-essential libssl-dev libffi-dev wkhtmltopdf xfonts-75dpi python2.7 python-pip

# Install wkhtmltopdf to support headless
RUN wget https://downloads.wkhtmltopdf.org/0.12/0.12.5/wkhtmltox_0.12.5-1.bionic_amd64.deb -P /tmp
RUN dpkg -i /tmp/wkhtmltox_0.12.5-1.bionic_amd64.deb

# Create app directory
RUN mkdir -p /opt/xero_automation
COPY . /opt/xero_automation

WORKDIR /opt/xero_automation
# Install app dependencies
RUN python setup.py install
RUN chmod +x xero_report.sh

CMD ["./xero_report.sh"]
