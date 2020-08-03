#!/usr/bin/env python

import argparse
import calendar
import datetime
import os
import pprint
import random
import shutil
import sys
import json

import pdfkit
import pystache

from openpyxl import Workbook
from xero_client import XeroClient

class XeroReport:
    def __init__(self, args):
        self.SYDNEY_TIME_OFFSET = datetime.timedelta(hours=11)
        self.MAX_DURATION = 12.0
        self.CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

        self.start_time = None
        self.end_time = None
        self.client_id = args.client_id
        self.client_secret = args.client_secret
        self.tenant_id = args.tenant_id
        self.refresh_token = args.refresh_token
        self.cache_users = {}
        self.cache_tasks = {}
        self.duration_weeks = 2
        self.output = args.output

        self.add_project_times(args.start_time, args.end_time)

        print("CI_PROJECT_ID=%s", os.getenv('CI_PROJECT_ID', None))
        self.xero_client = XeroClient(self.client_id, self.client_secret, self.tenant_id, self.refresh_token)
        self.DONT_VALIDATE_THESE_ITEMS = eval(os.environ.get('VALIDATION_EXCEPTIONS', '[]'))
        #TODO: change this with the Xero Contacts data
        #example of environment variable
        #OWNERS = "{ 'Project A': 'Neil', 'Non chargeable tasks': 'Adrian' }"
        OWNERS_FILE = os.path.join(self.CURRENT_DIRECTORY, ".owners")
        if os.path.isfile(OWNERS_FILE):
            owners = open(OWNERS_FILE).read().strip()
        else:
            owners = os.environ['OWNERS']
        self.OWNERS = eval(owners)
        print(self.OWNERS)


    def add_project_times(self, start_time, end_time):
        now = datetime.datetime.utcnow()
        self.filter = str(now)[0:4] + str(now)[5:7]
        print("Project Filter: {0}".format(self.filter))
        #set time stamps as per parameters
        if start_time:
            #adjust UTC to Sydney tz
            self.start_time = datetime.datetime.strptime(start_time + 'Z', '%Y-%m-%dZ') - self.SYDNEY_TIME_OFFSET
        if end_time:
            #adjust UTC to Sydney tz
            self.end_time = datetime.datetime.strptime(end_time + 'Z', '%Y-%m-%dZ') - self.SYDNEY_TIME_OFFSET
            #shift to the last second of the day
            self.end_time = self.end_time + datetime.timedelta(hours=23, minutes=59, seconds=59)

        #set up defaults unless they were setup before
        if not self.start_time:
            self.start_time = datetime.datetime.strptime(self.filter + "01" + 'Z', '%Y%m%dZ') - self.SYDNEY_TIME_OFFSET
        if not self.end_time:
            last_day = calendar.monthrange(now.year, now.month)[1]
            end_time_str = "{0}{1}Z".format(self.filter, last_day)
            self.end_time = datetime.datetime.strptime(end_time_str, '%Y%m%dZ') - self.SYDNEY_TIME_OFFSET
            #shift to the last second of the day
            self.end_time = self.end_time + datetime.timedelta(hours=23, minutes=59, seconds=59)


    def validate(self, output_dir, project_id, start_month, end_month):
        VALIDATION_ERROR = "Validation Error: "
        project_data = self.load_data(project_id)
        errors = []

        for tasks in project_data['tasks']:
            for item in tasks['items']:
                if item['id'] in self.DONT_VALIDATE_THESE_ITEMS:
                    continue
                task_date = datetime.datetime.strptime(item['date'], '%d-%b-%Y')
                error = None
                if task_date < start_month or task_date > end_month:
                    error = "{0} Out Of The Month Range - {1}".format(VALIDATION_ERROR, item)
                if item['duration'] > self.MAX_DURATION:
                    error = "{0} Is longer than the max duration {2} - {1}".format(VALIDATION_ERROR, item, self.MAX_DURATION)
                if error:
                    error = error.encode('utf-8').strip()
                if error:
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
        for user_id, user_time_list in tasks.items():
            user = self.user(user_id)
            user_total_duration = 0
            items = []

            for user_time_item in user_time_list:
                if 'duration' not in user_time_item.keys():
                    raise Exception("User_time_item has an item without a duration attribute. Item:{0} Items:{1}".format(
                        user_time_item, user_time_list))
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
        print('Generate report, project id=%s' % project_id)
        data = self.load_data(project_id)

        #pdf
        html = self.generate_html(data)
        self.generate_pdf(html, os.path.join(output_dir, self.report_name(project_id)))
        #xls
        project_name = data['projectName'].replace("/", "_")
        output_file = os.path.join(output_dir, project_name.replace(" ", "_") + '.xls')
        self.generate_xls(data, output_file, project_name)


    def generate_html(self, data):
        template_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'report.html')
        with open(template_file_path) as template_file:
            template = template_file.read()
        return pystache.render(template, data)

    def generate_pdf(self, html, output_file):
        pdfkit.from_string(html, output_file)

    def generate_xls(self, data, output_file, project_name):
        workbook = Workbook()
        workbook.remove_sheet(workbook.active)

        time_list = data

        #Write Header
        workbook_sheet = workbook.create_sheet(title=project_name)
        workbook_sheet.cell(row=1, column=1, value="Detailed Time")
        workbook_sheet.cell(row=2, column=1, value="Darumatic Pty Ltd")
        workbook_sheet.cell(row=3, column=1, value="For the period {} to {}".format(data['startTime'], data['endTime']))
        workbook_sheet.cell(row=6, column=1, value="Date")
        workbook_sheet.cell(row=6, column=2, value="Staff")
        workbook_sheet.cell(row=6, column=3, value="Task")
        workbook_sheet.cell(row=6, column=4, value="Description")
        workbook_sheet.cell(row=6, column=5, value="Total Time")
        workbook_sheet.cell(row=6, column=6, value="Project Name")
        workbook_sheet.cell(row=6, column=7, value="PO")
        workbook_sheet.cell(row=6, column=8, value="Project Owner")
        workbook_sheet.cell(row=4, column=1, value=project_name)

        ROW_OFFSET = 8

        PO = '' if not 'PO' in project_name else project_name.split()[project_name.split().index('PO') + 1]

        short_project_name = project_name if not "-" in project_name else project_name[:project_name.index("-")]
        #short_project_name_with_suffix = "{} - ".format(short_project_name)
        short_project_name = short_project_name.strip()
        owner = ""
        if short_project_name in self.OWNERS.keys():
            owner = self.OWNERS[short_project_name]
        else:
            raise Exception("Owner for proj '{}' not found".format(short_project_name))

        i_row = ROW_OFFSET
        for consultant in time_list['tasks']:
            for i, item in enumerate(consultant['items']):
                i_row = i_row + 1
                workbook_sheet.cell(row=i_row, column=1, value=item['date'])
                workbook_sheet.cell(row=i_row, column=2, value=item['userName'])
                workbook_sheet.cell(row=i_row, column=3, value=item['taskName'])
                workbook_sheet.cell(row=i_row, column=4, value=item['taskDescription'])
                workbook_sheet.cell(row=i_row, column=5, value=item['duration'])
                workbook_sheet.cell(row=i_row, column=6, value=short_project_name)
                workbook_sheet.cell(row=i_row, column=7, value=PO)
                workbook_sheet.cell(row=i_row, column=8, value=owner)

        workbook.save(output_file)
        print("Saving workbook in {}".format(output_file))

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
            'id': task['taskId'],
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
        return round(float(minutes) / 60, 4)

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

        # Create active projects json file
        os.mkdir(self.output+"/backup/")
        f = open(self.output+"/backup/all_projects.json", "w+")
        json.dump(self.get_active_projects(), f)
        f.close()

        for items in self.get_all_projects():
            for item in items['items']:
                if self.filter not in item['name']:
                    continue
                print('Generate Xero report for project %s between %s %s to %s' % (
                    item["projectId"], self.start_time, self.end_time, self.output))
                print("Name: {0}, ProjectID: {1}, Status: {2}, ContactId: {3}".format(item["name"], item["projectId"],
                                                                                      item["status"],
                                                                                      item["contactId"]))
                reporter.backup_data(item["projectId"], item["name"])
                reporter.generate_report(self.output, item["projectId"])


    def validate_active_projects_time_limits(self, reporter):
        month_start = self.start_time
        month_end = self.end_time + self.SYDNEY_TIME_OFFSET
        DARUMATIC_INIT_TIME = '2017-02-20'
        start_validation_time = DARUMATIC_INIT_TIME
        self.add_project_times(start_validation_time, None)
        end_validation_time = self.start_time + datetime.timedelta(days=5000)
        self.add_project_times(None, end_validation_time.strftime('%Y-%m-%d'))
        start_validation_time, end_validation_time = self.start_time, self.end_time

        print('Validating Active Projects..')
        print("Start Validation Time:{0} \n "
              "End Validation time:{1} \n "
              "Start Month:{2} \n "
              "End Month:{3} \n"
              "Start Time:{4} \n"
              "End Time:{5}".format(
            start_validation_time,
            end_validation_time,
            month_start,
            month_end,
            self.start_time,
            self.end_time
        ))
        errors = {}
        amount_of_errors = 0

        for items in self.get_all_projects():
            for item in items['items']:
                if self.filter not in item['name']:
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
        print("*" * 80)
        if amount_of_errors == 0:
            print("There are no errors. All tasks are validated successfully!!")
            return True
        else:
            print("There were a total of {0} errors.".format(amount_of_errors))
            return False

    def backup_data(self, project_id, project_name):
        # Create current project's folder
        project_folder = self.output + "/backup/" + project_name
        os.mkdir(project_folder)
        # Create time entry file
        xero_client = self.xero_client
        time_list = xero_client.time(project_id, self.start_time, self.end_time)
        time_list_file = open(project_folder+"/time_entries.json", "w+")
        json.dump(time_list, time_list_file)
        time_list_file.close()
        # Create tasks file
        task_list = xero_client.get_tasks(project_id)
        task_list_file = open(project_folder+"/tasks.json", "w+")
        json.dump(task_list, task_list_file)
        task_list_file.close()
        # Create users file
        user_list = []
        for time_entry in time_list:
            user_id = time_entry["userId"]
            user = xero_client.user(user_id)
            user_list.append(user)
        user_list_file = open(project_folder+"/users.json", "w+")
        json.dump(user_list, user_list_file)
        user_list_file.close()
        
    def close_previous_month_projects(self):
        counter = 0
        for items in self.get_all_projects():
            for item in items['items']:
                if self.filter not in item['name'] and item['status'] == "INPROGRESS":
                    data = {"status": "CLOSED"}
                    project_id = item["projectId"]
                    response = self.xero_client.patch_projects(
                        'https://api.xero.com/projects.xro/2.0/Projects/' + project_id, data)
                    if response == 204:
                        print("Closing project: " + item["name"] + "  SUCCEED!")
                        counter += 1
                    else:
                        print("Closing project: " + item["name"] + " FAILED!")
            if counter == 0:
                print("No projects have been closed")
            else:
                print("{0} projects have been closed".format(counter))



if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.realpath(__file__))

    parser = argparse.ArgumentParser("Generate Xero project reports")
    parser.add_argument('--client-id', type=str, required=True)
    parser.add_argument('--client-secret', type=str, required=True)
    parser.add_argument('--refresh-token', type=str, required=True)
    parser.add_argument('--tenant-id', type=str, required=True)
    parser.add_argument('--start-time', type=str, required=False, default=None)
    parser.add_argument('--end-time', type=str, required=False, default=None)
    parser.add_argument('--output', type=str, default=os.path.join(current_dir, "out"))

    command = sys.argv[1]
    args = parser.parse_args(sys.argv[2:])
    reporter = XeroReport(args)

    if command == "report":
        reporter.create_monthly_time_sheets(reporter)
    elif command == "close":
        reporter.close_previous_month_projects()
    elif command == "validate":
        if not(reporter.validate_active_projects_time_limits(reporter)):
            print("The Validate function failed. Please check the logs above for more information. \n"
                  "If any particular task item should be skipped, please add its id to the {0} \n"
                  " environment variable following this format: {1}".format("VALIDATION_EXCEPTIONS",
                                                                            "['task_id1', 'task_id1']"))
            sys.exit(1)
    else:
        print("Invalid command")
        sys.exit(2)

    print("Xero-Automation - Finished successfully!")
    sys.exit(0)
