# Dockerfile
FROM python:2.7

# Create app directory
RUN mkdir -p /opt/xero_automation
COPY . /opt/xero_automation
WORKDIR /opt/xero_automation
# Install app dependencies
RUN pip install -r requirements.txt

RUN chmod +x xero_report.sh
CMD ["./xero_report.sh"]
