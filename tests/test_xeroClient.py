import datetime
import json
import os
from unittest import TestCase

from xero_client import XeroClient

rsa_key_file = os.path.dirname(os.path.abspath(__file__)) + '/../rsa_key.pem'
with open(rsa_key_file) as keyfile:
    rsa_key = keyfile.read()
xero_client = XeroClient('RC0JPAB2DPT71YLTXHBVP6AWJFV73W', rsa_key)


class TestXeroClient(TestCase):
    def test_time(self):
        project_id = 'fa6649e7-f55d-40bb-8a31-55cf2fb18d5c'

        start_time = datetime.datetime.strptime("2018-12-01Z", "%Y-%m-%dZ")
        end_time = datetime.datetime.strptime("2018-12-30Z", "%Y-%m-%dZ")
        time_list = xero_client.time(project_id, start_time, end_time)
        for time in time_list:
            print json.dumps(time)
            user = xero_client.user(time['userId'])
            print json.dumps(user)

            task = xero_client.task(project_id, time['taskId'])
            print json.dumps(task)

            project = xero_client.project(project_id)
            print json.dumps(project)
            contact = xero_client.contact(project['contactId'])
            print json.dumps(contact)
