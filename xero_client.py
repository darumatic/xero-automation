import json
import time
import urllib

import requests

from xero.auth import PrivateCredentials


class XeroClient:
    def __init__(self, consumer_key, rsa_key):
        self.credentials = PrivateCredentials(consumer_key, rsa_key)
        self.headers = {'Accept': 'application/json'}
        self.MAX_TRIES = 9
        self.cache = {}

    def get_request(self, url):
        response = None
        tries = 0
        while True:
            print("Getting request...  {0}".format(url))
            if url in self.cache.keys():
                print("Request is cached")
                response = self.cache[url]
                break
            r = requests.get(url, headers=self.headers, auth=self.credentials.oauth)
            if r.status_code != 200:
                error = r.text
                too_many_requests = ("Max retries exceeded" in error) or ("rate%20limit%20exceeded" in error)
                if self.MAX_TRIES > tries and too_many_requests:
                    print("Max retries error. Sleeping 10 seconds before retrying...")
                    time.sleep(10)
                    tries = tries + 1
                    continue
                else:
                    raise Exception('failed to get request, response=' + error)
            else:
                response = r.json()
                self.cache[url] = response
                break
        return response

    def get_items(self, url, one_page=True):
        response = None
        if not one_page:
            response = []
            page = 1
            appender = "&" if ("?" in url.split("/")[-1]) else "?"
            while True:
                url_rq = "{0}{1}page={2}&pageSize=500".format(url, appender, page)
                r = self.get_request(url_rq)
                response.append(r)
                if r["pagination"]["pageCount"] > page:
                    page = page + 1
                else:
                    break
        else:
            response = self.get_request(url)
        return response

    def project(self, project_id):
        url = 'https://api.xero.com/projects.xro/2.0/projects/' + project_id
        return self.get_items(url)

    def get_projects(self):
        url = 'https://api.xero.com/projects.xro/2.0/projects'
        return self.get_items(url)

    def get_active_projects(self):
        return self.get_items('https://api.xero.com/projects.xro/2.0/projects?states=INPROGRESS')

    def task(self, project_id, task_id):
        url = 'https://api.xero.com/projects.xro/2.0/projects/' + project_id + '/tasks/' + task_id
        return self.get_items(url, one_page=True)

    def time(self, project_id, start_time, end_time):
        url = 'https://api.xero.com/projects.xro/2.0/projects/' + project_id + '/time?'
        if start_time is not None:
            url += 'dateAfterUtc=' + urllib.quote(self.to_json_timestamp(start_time)) + '&'
        if end_time is not None:
            url += 'dateBeforeUtc=' + urllib.quote(self.to_json_timestamp(end_time))

        body = self.get_items(url)
        return body['items']

    def user(self, user_id):
        url = 'https://api.xero.com/projects.xro/2.0/projectsusers'
        users = self.get_items(url, one_page=True)

        for user in users['items']:
            if user['userId'] == user_id:
                return user
        raise Exception('failed to load user, id=' + user_id)

    def contact(self, contact_id):
        url = 'https://api.xero.com/api.xro/2.0/Contacts/' + contact_id
        return self.get_items(url)

    def to_json_timestamp(self, utc_datetime):
        return json.dumps(utc_datetime.isoformat()).replace('"', '') + 'Z'
