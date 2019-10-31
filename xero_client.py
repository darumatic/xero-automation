import json
import urllib

import requests

from xero.auth import PrivateCredentials


class XeroClient:
    def __init__(self, consumer_key, rsa_key):
        self.credentials = PrivateCredentials(consumer_key, rsa_key)
        self.headers = {'Accept': 'application/json'}

    def get_all_items(self, url):
        response = []
        page = 1
        appender = "&" if ("?" in url.split("/")[-1]) else "?"
        while True:
            r = requests.get("{0}{1}page={2}&pageSize=500".format(url, appender, page), headers=self.headers, auth=self.credentials.oauth)
            if r.status_code != 200:
                error = r.text
                raise RuntimeError('failed to load project, response=' + error)
            r = r.json()
            response.append(r)
            if r["pagination"]["pageCount"] > page:
                page = page + 1
            else:
                break
        return response

    def project(self, project_id):
        url = 'https://api.xero.com/projects.xro/2.0/projects/' + project_id
        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=self.credentials.oauth)
        if r.status_code != 200:
            error = r.text
            raise Exception('failed to load project, response=' + error)
        return r.json()

    def get_projects(self):
        url = 'https://api.xero.com/projects.xro/2.0/projects'
        return self.get_all_items(url)

    def get_active_projects(self):
        return self.get_all_items('https://api.xero.com/projects.xro/2.0/projects?states=INPROGRESS')

    def get(self, url):
        return self.get_all_items(url)

    def task(self, project_id, task_id):
        url = 'https://api.xero.com/projects.xro/2.0/projects/' + project_id + '/tasks/' + task_id
        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=self.credentials.oauth)
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

        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=self.credentials.oauth)
        print self.credentials.oauth_token
        print r.status_code
        print r.text
        if r.status_code != 200:
            print("XXXXXXXXXXXXXX",r.status_code)
            error = r.text
            raise Exception('failed to load project time, response=' + error)

        body = r.json()
        return body['items']

    def user(self, user_id):
        url = 'https://api.xero.com/projects.xro/2.0/projectsusers'
        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=self.credentials.oauth)
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
        headers = {'Accept': 'application/json'}
        r = requests.get(url, headers=headers, auth=self.credentials.oauth)
        if r.status_code != 200:
            error = r.text
            raise Exception('failed to load contact, response=' + error)

        return r.json()

    def to_json_timestamp(self, utc_datetime):
        return json.dumps(utc_datetime.isoformat()).replace('"', '') + 'Z'
