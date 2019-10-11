import json
import urllib

import requests

from xero.auth import PrivateCredentials


class XeroClient:
    def __init__(self, consumer_key, rsa_key):
        self.consumer_key = consumer_key
        self.rsa_key = rsa_key

    def project(self, project_id):
        url = 'https://api.xero.com/projects.xro/2.0/projects/' + project_id
        credentials = PrivateCredentials(self.consumer_key, self.rsa_key)
        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=credentials.oauth)
        if r.status_code != 200:
            error = r.text
            raise Exception('failed to load project, response=' + error)

        return r.json()

    def task(self, project_id, task_id):
        url = 'https://api.xero.com/projects.xro/2.0/projects/' + project_id + '/tasks/' + task_id
        credentials = PrivateCredentials(self.consumer_key, self.rsa_key)
        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=credentials.oauth)
        if r.status_code != 200:
            error = r.text
            raise Exception('failed to load task, response=' + error)

        return r.json()

    def time(self, project_id, start_time, end_time):
        url = 'https://api.xero.com/projects.xro/2.0/projects/' + project_id + '/time?'
        if start_time is not None:
            url += 'dateAfterUtc=' + urllib.quote(self.to_json_timestamp(start_time)) + '&'
        if end_time is not None:
            url += 'dateBeforeUtc=' + urllib.quote(self.to_json_timestamp(end_time))

        print url
        credentials = PrivateCredentials(self.consumer_key, self.rsa_key)
        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=credentials.oauth)
        print credentials.oauth_token
        print r.status_code
        print r.text
        if r.status_code != 200:
            print "XXXXXXXXXXXXXX" + r.status_code
            error = r.text
            raise Exception('failed to load project time, response=' + error)

        body = r.json()
        return body['items']

    def user(self, user_id):
        url = 'https://api.xero.com/projects.xro/2.0/projectsusers'
        credentials = PrivateCredentials(self.consumer_key, self.rsa_key)
        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=credentials.oauth)
        if r.status_code != 200:
            error = r.text
            raise Exception('failed to load user, response=' + error)

        users = r.json()
        for user in users['items']:
            if user['userId'] == user_id:
                return user
        raise Exception('failed to load user, id=' + user_id)

    def contact(self, contact_id):
        url = 'https://api.xero.com/api.xro/2.0/Contacts/' + contact_id
        credentials = PrivateCredentials(self.consumer_key, self.rsa_key)
        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=credentials.oauth)
        if r.status_code != 200:
            error = r.text
            raise Exception('failed to load contact, response=' + error)

        return r.json()

    def to_json_timestamp(self, utc_datetime):
        return json.dumps(utc_datetime.isoformat()).replace('"', '') + 'Z'
