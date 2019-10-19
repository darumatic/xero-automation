#!/usr/bin/env python

import datetime
import getopt
import os
import random
import sys
from pprint import pprint

import pdfkit
import pystache

from xero_client import XeroClient


class XeroReport:
    def __init__(self, arguments):
        self.cache_users = {}
        self.cache_tasks = {}
        self.parse_options(arguments)
        self.xero_client = XeroClient(self.consumer_key, self.private_key)

    def parse_options(self, arguments):
        OPTIONS = 'p:s:e:u:d:o:k'
        opts = getopt.getopt(arguments, OPTIONS, ['key='])[0]

        self.project_ids = None
        self.start_time = None
        self.end_time = None
        self.consumer_key = None
        self.private_key = None
        self.duration_weeks = None
        self.output = None
        self.project_ids = None

        for o in opts:
            if o[0] == '-p':
                self.project_ids = [x.strip() for x in o[1].split(',')]
            elif o[0] == '-s' and o[1] != 'None':
                self.start_time = datetime.datetime.strptime(o[1] + 'Z', '%Y-%m-%dZ')
            elif o[0] == '-e' and o[1] != 'None':
                self.end_time = datetime.datetime.strptime(o[1] + 'Z', '%Y-%m-%dZ')
                self.end_time = self.end_time.replace(year=self.end_time.year, month=self.end_time.month, day=self.end_time.day, hour=23,
                                            minute=59, second=59, microsecond=999)
            elif o[0] == '-u':
                self.consumer_key = o[1]
            elif o[0] in ('-k', '--key'):
                self.private_key = o[1]
            elif o[0] == '-d' and o[1] is not None:
                self.duration_weeks = int(o[1])
            elif o[0] == '-o':
                self.output = o[1]

        if self.project_ids is None or \
                self.consumer_key is None or \
                self.private_key is None:
            raise RuntimeError("Missing required parameters")

        if self.start_time is None:
            now = datetime.datetime.utcnow()
            today = now.replace(year=now.year, month=now.month, day=now.day, hour=0, minute=0, second=0, microsecond=0)
            next_sunday = today + datetime.timedelta(days=6 - today.weekday())
            self.start_time = next_sunday - datetime.timedelta(days=7 * duration_weeks - 1)
            self.end_time = next_sunday
            self.end_time = self.end_time.replace(year=self.end_time.year, month=self.end_time.month, day=self.end_time.day, hour=23, minute=59,
                                        second=59, microsecond=999)

    def generate(self, output_dir):
        data = self.load_data()
        html = self.generate_html(data)
        self.generate_pdf(html, os.path.join(output_dir, self.report_name()))

    def load_data(self):
        xero_client = self.xero_client
        time_list = xero_client.time(self.project_id, self.start_time, self.end_time)
        project = xero_client.project(self.project_id)

        tasks = {}
        for time in time_list:
            user_id = time['userId']
            if user_id in tasks:
                user_time = tasks[user_id]
                user_time.append(self.task_item(time))
            else:
                user_time = [self.task_item(time)]
                tasks[user_id] = user_time

        total_hours = 0

        user_tasks = []
        for user_id, user_time_list in tasks.iteritems():
            user = self.user(user_id)
            user_total_duration = 0
            items = []

            for user_time_item in user_time_list:
                task_hours = user_time_item['duration']
                total_hours += task_hours
                user_total_duration += task_hours
                items.append(user_time_item)

            user_tasks.append({
                'userTotalDuration': user_total_duration,
                'userName': user['name'],
                'items': items
            })

        return {
            'startTime': self.start_time.strftime('%d %b %Y'),
            'endTime': self.end_time.strftime('%d %b %Y'),
            'totalHours': total_hours,
            'totalDays': self.round_hours_to_days(total_hours),
            'projectName': project['name'],
            'tasks': user_tasks
        }

    def generate_html(self, data):
        template_file_path = os.path.dirname(os.path.abspath(__file__)) + '/report.html'
        with open(template_file_path) as template_file:
            template = template_file.read()
        return pystache.render(template, data)

    def generate_pdf(self, html, output_file):
        pdfkit.from_string(html, output_file)

    def report_name(self):
        project = self.xero_client.project(self.project_id)
        project_name = project['name']
        report_name = ''
        skip = False
        for c in project_name:
            if c.isalpha() or c.isdigit():
                report_name += c.lower()
                skip = False
            else:
                if not skip:
                    report_name += '_'
                    skip = True

        report_name += '_'
        report_name += self.start_time.strftime('%d-%b-%Y').lower()
        report_name += '-'
        report_name += self.end_time.strftime('%d-%b-%Y').lower()
        report_name += '.' + ''.join(random.sample('0123456789', 3))
        report_name += '.pdf'
        return report_name

    def task_item(self, time):
        user = self.user(time['userId'])
        task = self.task(time['taskId'])

        return {
            'userName': user['name'],
            'taskName': task['name'],
            'taskDescription': time['description'],
            'date': datetime.datetime.strptime(time['dateUtc'][0:10] + 'Z', '%Y-%m-%dZ').strftime('%d-%b-%Y'),
            'duration': self.round_minutes_to_hours(time['duration'])
        }

    def round_minutes_to_hours(self, minutes):
        hours = int(minutes / 60)
        round_up = (minutes % 60) / 15
        if (round_up % 2 != 0):
            round_up += 1
        return hours + (round_up / 2 * 0.5)

    def round_hours_to_days(self, hours):
        return round(float(hours) / 8, 2)

    def user(self, user_id):
        xero_client = self.xero_client
        if user_id in self.cache_users:
            return self.cache_users[user_id]
        else:
            user = xero_client.user(user_id)
            self.cache_users[user_id] = user
            return user

    def task(self, task_id):
        xero_client = self.xero_client
        if task_id in self.cache_tasks:
            return self.cache_tasks[task_id]
        else:
            task = xero_client.task(self.project_id, task_id)
            self.cache_tasks[task_id] = task
            return task

    def get_active_projects(self):
        data = self.xero_client.get('https://api.xero.com/projects.xro/2.0/projects?states=INPROGRESS')
        for items in data:
            for item in items['items']:
                print("Name: {0}, ProjectID: {1}, Status: {2}, ContactId: {3}".format(item["name"], item["projectId"], item["status"], item["contactId"]))


if __name__ == "__main__":
    args = ['-p', 'a7f253e9-c842-4675-a90e-124a16f4891d',
            '-s', '2019-10-01',
            '-e', '2019-11-15',
            '-u', open("XERO_CONSUMER_KEY").read().strip(),
            '-d', '2',
            '-o', '/home/adrian/Nextcloud/Projects/xero-automation',
            '--key={0}'.format(open("privatekey.pem").read())]
    reporter = XeroReport(args)
    reporter.get_active_projects()