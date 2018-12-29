#!/usr/bin/env python

import datetime
import getopt
import os
import random
import sys

import pdfkit
import pystache

from xero_client import XeroClient


class XeroReport:
    def __init__(self, project_id, start_time, end_time, xero_client):
        self.project_id = project_id
        self.start_time = start_time
        self.end_time = end_time
        self.xero_client = xero_client
        self.cache_users = {}
        self.cache_tasks = {}

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
            'totalDays': int(total_hours / 24),
            'projectName': project['name'],
            'tasks': user_tasks
        }

    def generate_html(self, data):
        template_file_path = os.path.dirname(os.path.abspath(__file__)) + '/report.html'
        with open(template_file_path) as template_file:
            template = template_file.read()
        return pystache.render(template, data)

    def generate_pdf(self, html, output_file):
        print html
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
            'date': time['dateUtc'][0:10],
            'duration': int(time['duration'] / 60)
        }

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


if __name__ == '__main__':
    OPTIONS = 'p:s:e:u:k:d:o'
    opts = getopt.getopt(sys.argv[1:], OPTIONS)[0]

    project_ids = None
    start_time = None
    end_time = None
    consumer_key = None
    private_key = None
    duration_weeks = None
    output = None

    for o in opts:
        if o[0] == '-p':
            project_ids = [x.strip() for x in o[1].split(',')]
        elif o[0] == '-s' and o[1] != 'None':
            print o[1]
            start_time = datetime.datetime.strptime(o[1] + 'Z', '%Y-%m-%dZ')
            print start_time
        elif o[0] == '-e' and o[1] != 'None':
            end_time = datetime.datetime.strptime(o[1] + 'Z', '%Y-%m-%dZ')
            end_time = end_time.replace(year=end_time.year, month=end_time.month, day=end_time.day, hour=23, minute=59, second=59, microsecond=999)
        elif o[0] == '-u':
            consumer_key = o[1]
        elif o[0] == '-k':
            private_key = o[1]
        elif o[0] == '-d' and o[1] is not None:
            duration_weeks = int(o[1])
        elif o[0] == '-o':
            output = o[1]

    if project_ids is None or \
            consumer_key is None or \
            private_key is None:
        print """Missing required parameters
                """
        sys.exit(1)

    if start_time is None:
        now = datetime.datetime.utcnow()
        today = now.replace(year=now.year, month=now.month, day=now.day, hour=0, minute=0, second=0, microsecond=0)
        next_sunday = today + datetime.timedelta(days=6 - today.weekday())
        start_time = next_sunday - datetime.timedelta(days=7 * duration_weeks - 1)
        end_time = next_sunday
        end_time = end_time.replace(year=end_time.year, month=end_time.month, day=end_time.day, hour=23, minute=59, second=59, microsecond=999)

    xero_client = XeroClient(consumer_key, private_key)
    for project_id in project_ids:
        print 'Generate Xero report for project %s between %s %s' % (project_id, start_time, end_time)
        report = XeroReport(project_id, start_time, end_time, xero_client)
        report.generate(output)
