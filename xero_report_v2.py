#!/usr/bin/env python

import datetime
import getopt
import os
import pprint
import random
import shutil

import pdfkit
import pystache

from xero_client_v2 import XeroClient


class XeroReport:
    def __init__(self, arguments):
        self.SYDNEY_TIME_OFFSET = datetime.timedelta(hours=11)
        self.cache_users = {}
        self.cache_tasks = {}
        self.start_time = None
        self.end_time = None
        self.duration_weeks = None
        self.output = None
        self.parse_options(arguments)
        self.xero_client = XeroClient(self.client_id, self.client_secret, self.tenant_id, self.refresh_token)

    def add_project_times(self, start_time, end_time):
        if start_time:
            # adjust UTC to Sydney tz
            self.start_time = datetime.datetime.strptime(start_time + 'Z', '%Y-%m-%dZ') - self.SYDNEY_TIME_OFFSET
        if end_time:
            # adjust UTC to Sydney tz
            self.end_time = datetime.datetime.strptime(end_time + 'Z', '%Y-%m-%dZ') - self.SYDNEY_TIME_OFFSET
            # shift to the last second of the day
            self.end_time = self.end_time + datetime.timedelta(hours=23, minutes=59, seconds=59)

    def parse_options(self, arguments):
        OPTIONS = 'p:s:e:t:d:o:c:k:'
        opts = getopt.getopt(arguments, OPTIONS, ['key='])[0]

        for o in opts:
            if o[0] in ('-p'):
                self.tenant_id = o[1]
            elif o[0] == '-s' and o[1] != 'None':
                self.add_project_times(o[1], None)
            elif o[0] == '-e' and o[1] != 'None':
                self.add_project_times(None, o[1])
            elif o[0] in ('-t'):
                self.refresh_token = o[1]
            elif o[0] == '-d' and o[1] is not None:
                self.duration_weeks = int(o[1])
            elif o[0] == '-o':
                self.output = o[1]
            elif o[0] == '-c':
                self.client_id = o[1]
            elif o[0] == '-k':
                self.client_secret = o[1]

        if self.start_time is None:
            now = datetime.datetime.utcnow()
            today = now.replace(year=now.year, month=now.month, day=now.day, hour=0, minute=0, second=0, microsecond=0)
            next_sunday = today + datetime.timedelta(days=6 - today.weekday())
            self.start_time = next_sunday - datetime.timedelta(days=7 * self.duration_weeks - 1)
            self.end_time = next_sunday
            self.end_time = self.end_time.replace(year=self.end_time.year, month=self.end_time.month,
                                                  day=self.end_time.day, hour=23, minute=59,
                                                  second=59, microsecond=999)

    def validate(self, output_dir, project_id, start_month, end_month):
        VALIDATION_ERROR = "Validation Error: "
        project_data = self.load_data(project_id)
        errors = []

        for tasks in project_data['tasks']:
            for item in tasks['items']:
                task_date = datetime.datetime.strptime(item['date'], '%d-%b-%Y')
                if task_date < start_month or task_date > end_month:
                    error = "{0} Out Of The Month Range - {1}".format(VALIDATION_ERROR, item)
                    print(error)
                    errors.append(error)

        return errors

    def load_data(self, project_id):
        xero_client = self.xero_client
        time_list = xero_client.time(project_id, self.start_time, self.end_time)
        project = xero_client.project(project_id)

        tasks = {}
        for time in time_list:
            user_id = time['userId']
            if user_id in tasks:
                user_time = tasks[user_id]
                user_time.append(self.task_item(time, project_id))
            else:
                user_time = [self.task_item(time, project_id)]
                tasks[user_id] = user_time

        total_hours = 0

        user_tasks = []
        for user_id, user_time_list in tasks.iteritems():
            user = self.user(user_id)
            user_total_duration = 0
            items = []

            for user_time_item in user_time_list:
                if 'duration' not in user_time_item.keys():
                    print("Warning, user_time_item has an item without a duration attribute. Item:{0} Items:{1}".format(
                        user_time_item, user_time_list))
                    continue
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
            'startTime': (self.start_time + self.SYDNEY_TIME_OFFSET).strftime('%d %b %Y'),
            'endTime': (self.end_time + self.SYDNEY_TIME_OFFSET).strftime('%d %b %Y'),
            'totalHours': total_hours,
            'totalDays': self.round_hours_to_days(total_hours),
            'projectName': project['name'],
            'tasks': user_tasks
        }

    def generate_report(self, output_dir, project_id):
        data = self.load_data(project_id)
        html = self.generate_html(data)
        self.generate_pdf(html, os.path.join(output_dir, self.report_name(project_id)))

    def generate_html(self, data):
        template_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report.html')
        with open(template_file_path) as template_file:
            template = template_file.read()
        return pystache.render(template, data)

    def generate_pdf(self, html, output_file):
        pdfkit.from_string(html, output_file)

    def report_name(self, project_id):
        project = self.xero_client.project(project_id)
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

    def task_item(self, time, project_id):
        user = self.user(time['userId'])
        task = self.task(time['taskId'], project_id)

        sydney_time = datetime.datetime.strptime(time['dateUtc'], '%Y-%m-%dT%H:%M:%SZ') + self.SYDNEY_TIME_OFFSET
        ret = {
            'userName': user['name'],
            'taskName': task['name'],
            'date': sydney_time.strftime('%d-%b-%Y'),
            'duration': self.round_minutes_to_hours(time['duration'])
        }

        try:
            description = time['description']
        except Exception as e:
            print("Error capturing description from:{0} Falling back to empty string".format(str(time)))
            description = ' '

        ret['taskDescription'] = description

        return ret

    def round_minutes_to_hours(self, minutes):
        # hours = int(minutes / 60)
        # round_up = (minutes % 60) / 15
        # if (round_up % 2 != 0):
        #     round_up += 1
        # return hours + (round_up / 2 * 0.5)
        return round(float(minutes) / 60, 3)

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

    def task(self, task_id, project_id):
        xero_client = self.xero_client
        if task_id in self.cache_tasks:
            return self.cache_tasks[task_id]
        else:
            task = xero_client.task(project_id, task_id)
            self.cache_tasks[task_id] = task
            return task

    def get_all_projects(self):
        return self.xero_client.get_items('https://api.xero.com/projects.xro/2.0/projects',
                                          one_page=False)

    def get_active_projects(self):
        return self.xero_client.get_items('https://api.xero.com/projects.xro/2.0/projects?states=INPROGRESS',
                                          one_page=False)

    def print_active_projects(self):
        for items in self.get_active_projects():
            for item in items['items']:
                print("Name: {0}, ProjectID: {1}, Status: {2}, ContactId: {3}".format(item["name"], item["projectId"],
                                                                                      item["status"],
                                                                                      item["contactId"]))

    def create_monthly_time_sheets(self, reporter):
        if os.path.exists(self.output):
            shutil.rmtree(self.output)
            os.makedirs(self.output)
        else:
            os.makedirs(self.output)
        for items in self.get_all_projects():
            for item in items['items']:
                if 'OpenShift Implementation - 202001' not in item['name']:
                    continue
                print 'Generate Xero report for project %s between %s %s to %s' % (
                    item["projectId"], self.start_time, self.end_time, self.output)
                print("Name: {0}, ProjectID: {1}, Status: {2}, ContactId: {3}".format(item["name"], item["projectId"],
                                                                                      item["status"],
                                                                                      item["contactId"]))
                reporter.generate_report(self.output, item["projectId"])

    def validate_active_projects_time_limits(self, reporter):
        month_start = self.start_time
        month_end = self.end_time + self.SYDNEY_TIME_OFFSET
        start_validation_time = '2017-02-20'
        self.add_project_times(start_validation_time, None)
        end_validation_time = self.start_time + datetime.timedelta(days=5000)
        self.add_project_times(None, end_validation_time.strftime('%Y-%m-%d'))
        start_validation_time, end_validation_time = self.start_time, self.end_time

        print('Validating Active Projects..')
        print("Start Validation Time:{0} \n End Validation time:{1} \n Start Month:{2} \n End Month:{3}".format(
            start_validation_time, end_validation_time, month_start, month_end))
        errors = {}
        amount_of_errors = 0

        for items in self.get_all_projects():
            for item in items['items']:
                if '202001' not in item['name']:
                    continue
                print("Name: {0}, ProjectID: {1}, Status: {2}, ContactId: {3}".format(item["name"], item["projectId"],
                                                                                      item["status"],
                                                                                      item["contactId"]))
                errors[item["name"]] = []
                project_errors = reporter.validate(self.output, item["projectId"], month_start, month_end)
                errors[item["name"]].append(project_errors)
                amount_of_errors = len(project_errors) + amount_of_errors

        print("*" * 80)
        print("List of Validation errors")
        pprint.pprint(errors)
        if amount_of_errors == 0:
            print("There are no errors. All tasks are validated successfully!!")
        else:
            print("There were a total of {0} errors.".format(amount_of_errors))


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.realpath(__file__))

    args = ['-s', '2020-01-31',
            '-e', '2020-01-31',
            '-p', '2e741d6d-cf4e-4ccb-83d2-6bbc0d0f3cb8',
            '-t', open(os.path.join(current_dir, "XERO_REFRESH_TOKEN")).read().strip(),
            '-d', '2',
            '-o', os.path.join(current_dir, "out"),
            '-c', "1744C5B5478644999D632BC16B3D7D7C",
            '-k', open(os.path.join(current_dir, "XERO_CLIENT_SECRET")).read().strip()]
    reporter = XeroReport(args)
    pprint.pprint(reporter.get_active_projects())
    reporter.create_monthly_time_sheets(reporter)
    # reporter.validate_active_projects_time_limits(reporter)
