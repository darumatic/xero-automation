import datetime
import os
from unittest import TestCase

from xero_client import XeroClient
from xero_report import XeroReport

rsa_key_file = os.path.dirname(os.path.abspath(__file__)) + '/../rsa_key.pem'
with open(rsa_key_file) as keyfile:
    rsa_key = keyfile.read()
xero_client = XeroClient('RC0JPAB2DPT71YLTXHBVP6AWJFV73W', rsa_key)


class TestXeroProjectReport(TestCase):
    def test_generate_html(self):
        project_id = 'fa6649e7-f55d-40bb-8a31-55cf2fb18d5c'
        start_time = datetime.datetime.strptime("2018-12-01Z", "%Y-%m-%dZ")
        end_time = datetime.datetime.strptime("2018-12-30Z", "%Y-%m-%dZ")
        report = XeroReport(project_id, start_time, end_time, xero_client)
        output_dir = os.path.dirname(os.path.abspath(__file__))
        report.generate(output_dir)
