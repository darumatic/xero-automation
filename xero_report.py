#!/usr/bin/env python

import datetime
import getopt
import os
import pprint
import random
import shutil
import pdfkit
import pystache

from xero_client import XeroClient


class GMTSydney(datetime.tzinfo):
     def utcoffset(self, dt):
         return timedelta(hours=1) + self.dst(dt)
     def dst(self, dt):
         # DST starts last Sunday in March
         d = datetime(dt.year, 4, 1)   # ends last Sunday in October
         self.dston = d - timedelta(days=d.weekday() + 1)
         d = datetime(dt.year, 11, 1)
         self.dstoff = d - timedelta(days=d.weekday() + 1)
         if self.dston <=  dt.replace(tzinfo=None) < self.dstoff:
             return timedelta(hours=1)
         else:
             return timedelta(0)
     def tzname(self,dt):
          return "GMT +11"

class XeroReport:
    def __init__(self, arguments):
        self.cache_users = {}
        self.cache_tasks = {}
        self.start_time = None
        self.end_time = None
        self.consumer_key = None
        self.private_key = None
        self.duration_weeks = None
        self.output = None
        self.parse_options(arguments)
        self.xero_client = XeroClient(self.consumer_key, self.private_key)

    def add_project_times(self, start_time, end_time):
        if start_time:
            self.start_time = datetime.datetime.strptime(start_time + 'Z', '%Y-%m-%dZ')
        if end_time:
            self.end_time = datetime.datetime.strptime(end_time + 'Z', '%Y-%m-%dZ')
            self.end_time = self.end_time.replace(year=self.end_time.year, month=self.end_time.month,
                                                  day=self.end_time.day, hour=23,
                                                  minute=59, second=59, microsecond=999)

    def parse_options(self, arguments):
        OPTIONS = 'p:s:e:u:d:o:k'
        opts = getopt.getopt(arguments, OPTIONS, ['key='])[0]

        for o in opts:
            if o[0] == '-s' and o[1] != 'None':
                self.add_project_times(o[1], None)
            elif o[0] == '-e' and o[1] != 'None':
                self.add_project_times(None, o[1])
            elif o[0] == '-u':
                self.consumer_key = o[1]
            elif o[0] in ('-k', '--key'):
                self.private_key = o[1]
            elif o[0] == '-d' and o[1] is not None:
                self.duration_weeks = int(o[1])
            elif o[0] == '-o':
                self.output = o[1]

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
                task_date = datetime.datetime.strptime(item['date'],'%d-%b-%Y')
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
                user_time_item['date'] = datetime.datetime.strptime(user_time_item['date'],'%d-%b-%Y').astimezone(datetime.tzinfo(GMTSydney()))
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

    def generate(self, output_dir, project_id):
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

        ret = {}
        try:
            ret = {
                'userName': user['name'],
                'taskName': task['name'],
                'taskDescription': '{0}'.format(time['description'] if time['description'] else ''),
                'date': datetime.datetime.strptime(time['dateUtc'][0:10] + 'Z', '%Y-%m-%dZ').strftime('%d-%b-%Y'),
                'duration': self.round_minutes_to_hours(time['duration'])
            }
        except Exception as e:
            print("Error getting task items. For time:{0} project_id:{1} user:{2} task:{3}".format(time, project_id, user, task))
            print("Exception: {0}".format(str(e)))

        return ret

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

    def task(self, task_id, project_id):
        xero_client = self.xero_client
        if task_id in self.cache_tasks:
            return self.cache_tasks[task_id]
        else:
            task = xero_client.task(project_id, task_id)
            self.cache_tasks[task_id] = task
            return task

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
        for items in self.get_active_projects():
            for item in items['items']:
                if 'OneGov - PO 45453559 - 201910' not in item['name']:
                    continue
                print 'Generate Xero report for project %s between %s %s to %s' % (
                    item["projectId"], self.start_time, self.end_time, self.output)
                print("Name: {0}, ProjectID: {1}, Status: {2}, ContactId: {3}".format(item["name"], item["projectId"],
                                                                                      item["status"],
                                                                                      item["contactId"]))
                reporter.generate(self.output, item["projectId"])

    def validate_active_projects(self, reporter):
        #todo: end time should be start + 100 years
       # self.add_project_times('2017-02-20', '2099-02-20')
        month_start = datetime.datetime.strptime('2019-10-01' + 'Z', '%Y-%m-%dZ')
        month_end = datetime.datetime.strptime('2019-10-31' + 'Z', '%Y-%m-%dZ')
        errors = {}

        for items in self.get_active_projects():
            for item in items['items']:
                # if "L&G - Front End - PO 45457767 - 201910" not in item["name"]:
                #     continue
                if '201910' not in item['name']:
                    continue
                print('Validating Active Projects..')
                print("Name: {0}, ProjectID: {1}, Status: {2}, ContactId: {3}".format(item["name"], item["projectId"],
                                                                                      item["status"],
                                                                                      item["contactId"]))
                errors[item["name"]] = []
                project_errors = reporter.validate(self.output, item["projectId"], month_start, month_end)
                errors[item["name"]].append(project_errors)
                break

        print("*" * 80)
        print("List of Validation errors")
        pprint.pprint(errors)


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.realpath(__file__))
    # future = datetime.datetime.now() + datetime.timedelta(days=10000)

    args = ['-s', '2019-09-10',
            '-e', '2019-09-30',
            '-u', open(os.path.join(current_dir, "XERO_CONSUMER_KEY")).read().strip(),
            '-d', '2',
            '-o', os.path.join(current_dir, "out"),
            '--key={0}'.format(open("privatekey.pem").read())]
    reporter = XeroReport(args)
    reporter.create_monthly_time_sheets(reporter)
    #reporter.validate_active_projects(reporter)
