import argparse
import datetime
import enum
import json
import os
import re
import ssl
import sys
from pprint import pprint

import gspread
from gspread.models import Spreadsheet, Worksheet
from oauth2client.service_account import ServiceAccountCredentials

from xero_client import XeroClient
from xero_email_sender import XeroEmailSender

ssl_version = ssl.PROTOCOL_TLSv1_2


class XeroSpreadSheet:
    class Columns(enum.Enum):
        """
        Column headings for the spreadsheet

        - If the spreadsheet headings were to change, change them here
        - E.g. to access `total_budget`, do `XeroSpreadSheet.columns.total_budget.value`
        """

        PO = "PO"
        PROJECT_NAME = "Project"
        QUOTE = "quote"
        BUDGET_CONSUMED = "Budget Consumed"
        BUDGET_REMAINING = "Budget Remaining"
        TOTAL_BUDGET = "Total Budget"
        TOTAL_BUDGET_GST = "Total + GST"
        END_DATE_ESTIMATE = "End Date Estimate"
        DAYS_REMAINING = "Days Remaining"
        TOTAL_DAYS = "Total Days"
        PERCENTAGE_CONSUMED = "% Consumed"
        WEEKS_LEFT = "Weeks Left"
        BURN_RHYTHM = "Burn Rythm Days/pw"
        RATE = "Rate"
        ERAF = "ERFA"
        NOTIFY = "Notify"

    def __init__(self, url, credentials):
        self.sheet = self._get_spreadsheet(url, credentials)
        self.data = self.get_data()

    # FIXME THIS FUNCTION DOESN'T SEEM TO WORK PROPERLY
    # def find_column(self, column_name):
    #     for i, value in enumerate(self.columns):
    #         if value == column_name:
    #             return i

    #     return -1

    def _get_spreadsheet(self, url, credential) -> Worksheet:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive",
        ]

        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            credential, scope
        )
        client = gspread.authorize(credentials)

        sheet = client.open_by_url(url).sheet1

        return sheet

    def get_data(self):
        return self.sheet.get_all_records()

    # def find_col_by_heading(self, target: str) -> int:
    #     """
    #     Searches the heading row for a string

    #     - Returns the column index on success (indexed from 1)
    #     - Returns -1 when not found
    #     """
    #     heading_row = self.sheet.row_values(1)

    #     for i, heading in enumerate(heading_row):
    #         if target == heading:
    #             return i + 1    # Spreadsheet indexes from 1

    #     return -1

    def find_row_by_po(self, po):
        try:
            for i, row in enumerate(self.data):
                if str(row[self.Columns.PO.value]) == po:
                    return i + 2
        except Exception:
            pass

        return -1

    def find_row_by_qu(self, qu):
        try:
            target_qu = "QU " + qu
            for i, row in enumerate(self.data):
                if row[self.Columns.QUOTE.value] == target_qu:
                    return i + 2
        except Exception:
            pass

        return -1

    def update_budget_consumed(self, row, value):
        column_index = self.find_column("Budget Consumed")
        if column_index < 0:
            raise Exception("Spreadsheet missing column 'Budget Consumed'")
        self.sheet.update_cell(row, column_index, value)


class XeroSpreadSheetReport:
    class Warnings(enum.Enum):
        """
        Types of warnings that can be generated
        """

        OTHER = 0
        OVER_BUDGET_THRESHOLD = 1
        DAYS_REMAINING = 2
        PROJECT_NAME_INVALID = 3
        PROJECT_NOT_IN_XERO = 4
        PROJECT_NOT_IN_SPREADSHEET = 5
        SPREADSHEET_PROJECT_NO_PO_AND_QU = 6

    def __init__(self, args):
        # TODO update timezones to pytz?
        self.SYDNEY_TIME_OFFSET = datetime.timedelta(hours=11)
        self.MAX_DURATION = 12.0
        self.CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

        self.client_id = args.client_id
        self.client_secret = args.client_secret
        self.tenant_id = args.tenant_id
        self.refresh_token = args.refresh_token
        self.url = args.url
        self.credential = args.credential
        self.emails = self._get_emails_to_notify(args.emails_file)
        self.suppress_emails = args.suppress_emails
        self.budget_warn_percentage = args.budget_warn_percentage
        self.days_remaining_warn_threshold = args.days_remaining_warn_threshold
        self.warning_strings = {}
        self.xero_client = XeroClient(
            self.client_id, self.client_secret, self.tenant_id, self.refresh_token
        )

        self.spreadsheet = XeroSpreadSheet(self.url, self.credential)

        print("XeroSpreadSheetReport init OK")

    def _get_emails_to_notify(self, email_json_filename: str) -> dict:
        """
        Parse emails in the following json format:

        ```json
        {
            "Name": "email@example.com",
            "John Doe": "john_doe@example.com",
            "Jane Smith": "jane_smith@example.com"
        }
        ```
        """
        # TODO update docs with this requirement
        if email_json_filename is None:
            print("Warning: No emails supplied for budget alerts")
            return {}

        with open(email_json_filename, "r") as file:
            emails = json.loads(file.read())

            try:
                assert isinstance(emails, dict)
            except AssertionError:
                raise Exception(
                    f"{email_json_filename} isn't in the right format, see readme for format info"
                )

            print(f"Successfully parsed {email_json_filename}:")
            pprint(emails)
            return emails

    def parse_project_name(self, name):
        tokens = re.findall(r"[\w']+", name)
        parsed = {"PO": None, "QU": None}

        for i, token in enumerate(tokens):
            if i < len(tokens) - 1:
                if token.upper() == "QU":
                    parsed["QU"] = tokens[i + 1]
                elif token.upper() == "PO":
                    parsed["PO"] = tokens[i + 1]

        return parsed

    def sync(self):
        self.spreadsheet.get_data()

        projects = self.xero_client.get_projects()
        pprint(projects)  # FIXME REMOVE DEBUG PRINT

        warnings = []
        changes = []
        visited_po = set()
        visited_qu = set()

        # Iterates through every project on Xero
        for project in projects["items"]:
            # Checks whether the Xero project has a valid name
            project_name = self.parse_project_name(project["name"])
            po = project_name["PO"]
            qu = project_name["QU"]
            if po is None and qu is None:
                warnings.append(
                    {
                        "name": project["name"],
                        "type": self.Warnings.PROJECT_NAME_INVALID
                        # "messages": ["Invalid project name format, missing PO"],
                    }
                )
                continue

            # Checks whether the current Xero project is present in the spreadsheet
            row_found_by_po = self.spreadsheet.find_row_by_po(po)
            row_found_by_qu = self.spreadsheet.find_row_by_qu(qu)

            # If neither the PO nor QU were present in the spreadsheet
            if row_found_by_po < 0 and row_found_by_qu < 0:
                warnings.append(
                    {
                        "name": project["name"],
                        "type": self.Warnings.PROJECT_NOT_IN_SPREADSHEET,
                        "po": po,
                        "qu": qu
                        # "messages": [
                        #     "Cant find project in spreadsheet, PO={}, QU={}".format(
                        #         po, project_name["QU"]
                        #     )
                        # ],
                    }
                )
                continue

            budget_consumed = project["totalTaskAmount"]["value"]

            # FIXME remove debug print and enable update
            print(f"totalTaskAmount = {budget_consumed}")

            changes.append({"name": project["name"], "budgetConsumed": budget_consumed})
            # spread_sheet.update_budget_consumed(row + 2, budget_consumed)
            visited_po.add(po)
            visited_qu.add(qu)

        if len(changes) > 0:
            print("\nUpdated {} projects:".format(len(changes)))

            for change in changes:
                print(
                    "- {} update budget consumed to be {}".format(
                        change["name"], change["budgetConsumed"]
                    )
                )

        # Iterates through the entries in the spreadsheet
        for data in self.spreadsheet.data:
            # Checks for empty PO and QU
            if (
                data[self.spreadsheet.Columns.PO.value] == ""
                and data[self.spreadsheet.Columns.QUOTE.value] == ""
            ):
                warnings.append(
                    {
                        "name": data[self.spreadsheet.Columns.PROJECT_NAME.value],
                        "type": self.Warnings.SPREADSHEET_PROJECT_NO_PO_AND_QU,
                    }
                )
                continue

            # Checks whether the PO was in Xero
            if str(data[self.spreadsheet.Columns.PO.value]) not in visited_po:
                # If PO wasn't found, check the QU instead
                # Keeps only numbers in the string
                quote_number = "".join(
                    list(
                        [
                            char
                            for char in data[self.spreadsheet.Columns.QUOTE.value]
                            if char.isnumeric()
                        ]
                    )
                )
                if quote_number not in visited_qu:
                    warnings.append(
                        {
                            "name": data["Project"],
                            "type": self.Warnings.PROJECT_NOT_IN_XERO
                            # "messages": ["Cant find project in Xero"],
                        }
                    )
                    continue

        # if len(warnings) > 0:
        #     print("\nThere are {} warnings:".format(len(warnings)))
        #     for warning in warnings:
        #         print("- {}".format(warning["name"]))
        #         for message in warning["messages"]:
        #             print("  {}".format(message))

        #     exit(1)

        warning_strings = self._generate_warning_strings_sync(warnings)
        print("Google spreadsheet - Synced successfully!")

    def _generate_warning_strings_sync(self, warnings: list) -> dict:
        """
        Generates warning strings from the sync function

        Different from the normal `generate_warning_strings` because the sync function's warnings are of a different format

        Returns a dictionary

        - The keys are the warning types
        - The values are the warning messages
        """

        warnings_dict = {}
        for warning in warnings:
            if warning["type"] == self.Warnings.PROJECT_NAME_INVALID:
                message = f"'{warning['name']}' on Xero is invalid"

            elif warning["type"] == self.Warnings.PROJECT_NOT_IN_XERO:
                message = f"'{warning['name']}' couldn't be found in Xero"

            elif warning["type"] == self.Warnings.PROJECT_NOT_IN_SPREADSHEET:
                message = (
                    f"'{warning['name']}' couldn't be found in the spreadsheet. "
                    f"(PO: {warning['po'] if warning['po'] != None else 'N/A'}, "
                    f"Quote: {warning['qu'] if warning['qu'] != None else 'N/A'})"
                )

            elif warning["type"] == self.Warnings.SPREADSHEET_PROJECT_NO_PO_AND_QU:
                message = f"'{warning['name']}' is missing a PO and quote"

            else:
                raise Exception(f"{warning['type']} isn't a valid warning type")

            # Adds the message to the return dictionary
            if warning["type"] in warnings_dict:
                warnings_dict[warning["type"]].append(message)
            else:
                warnings_dict[warning["type"]] = [message]

            # Adds the message to the object's dictionary attribute
            if warning["type"] in self.warning_strings:
                self.warning_strings[warning["type"]].append(message)
            else:
                self.warning_strings[warning["type"]] = [message]

        return warnings_dict

    def check_remaining_days(self) -> list:
        """
        Returns a list of dictionaries of projects that have `days` left before its estimated end time

        - Also adds the list to its own `warnings` attribute
        - Dictionary has the spreadsheet column headings as keys (return value of `Worksheet.get_all_records()`)
        - Assumes this script is run once per day
        - Rounds the number in the spreadsheet to the nearest integer
        - Uses equality to check
        """
        self.spreadsheet.get_data()

        entries_requiring_attention = []
        for entry in self.spreadsheet.data:
            if (
                round(entry[self.spreadsheet.Columns.DAYS_REMAINING.value])
                == self.days_remaining_warn_threshold
            ):
                entries_requiring_attention.append(entry)

        return entries_requiring_attention
        # TODO email functionality

        # column_index = self.spreadsheet.find_col_by_heading("Days Remaining")
        # print(f"column number is {column_index}")

        # # Removes the top cell (heading)
        # column_values = self.spreadsheet.sheet.col_values(column_index)[1:]

        # # Appends the sheet index to the list if days remaining is `days`
        # indexes_requiring_alert = []
        # for i, days_remaining in enumerate(column_values):
        #     if threshold == round(float(days_remaining)):
        #         indexes_requiring_alert.append(i + 2)

        # for index in indexes_requiring_alert:
        #     pprint(self.spreadsheet.sheet.row_values(index))

    def check_budget_consumed(self) -> list:
        """
        Returns a list of dictionaries of projects that are over the threshold

        - Also adds the list to its own `warnings` attribute
        - Dictionary has the spreadsheet column headings as keys (return value of `Worksheet.get_all_records()`)
        """
        # TODO
        self.spreadsheet.get_data()

        over_threshold_entries = []

        # Iterates through the rows looking for over threshold entries
        # Appends the entries to their respective lists if any are found
        for entry in self.spreadsheet.data:
            budget_consumed = self._string_to_float(
                entry[self.spreadsheet.Columns.BUDGET_CONSUMED.value]
            )
            total_budget = self._string_to_float(
                entry[self.spreadsheet.Columns.TOTAL_BUDGET.value]
            )
            consumption_percentage = (
                self._string_to_float(
                    entry[self.spreadsheet.Columns.PERCENTAGE_CONSUMED.value]
                )
                / 100
            )

            if consumption_percentage >= self.budget_warn_percentage:
                over_threshold_entries.append(entry)

        # Output printing
        if len(over_threshold_entries) == 0:
            print(
                f"No projects consuming {self.budget_warn_percentage * 100}% or more budget"
            )
        else:
            print(
                f"{len(over_threshold_entries)} projects consuming {self.budget_warn_percentage * 100}% or more budget:"
            )
            pprint(over_threshold_entries)

        self._generate_warning_strings(
            over_threshold_entries, self.Warnings.OVER_BUDGET_THRESHOLD
        )

        return over_threshold_entries

        # consumed_column_index = self.spreadsheet.find_col_by_heading("Budget Consumed")
        # total_column_index = self.spreadsheet.find_col_by_heading("Total Budget")

        # # Gets the target columns and strips the heading from the list
        # consumed_list = self.spreadsheet.sheet.col_values(consumed_column_index)[1:]
        # total_list = self.spreadsheet.sheet.col_values(total_column_index)[1:]

        # # Sanity check
        # if len(consumed_list) != len(total_list):
        #     raise Exception("Budget Consumed and Total Budget columns aren't the same size")

        # # Indexes are spreadsheet indexes, i.e. the first entry has index 2
        # indexes_over_budget = []
        # index_over_threshold = []
        # # pprint(consumed_list[3])
        # # pprint(total_list[1])
        # # Iterates through the 2 lists looking for budget above threshhold
        # # FIXME handle currency sign
        # for i, _ in enumerate(consumed_list):
        #     # Checks for over budget
        #     if self._string_to_float(consumed_list[i]) >= self._string_to_float(total_list[i]):
        #         indexes_over_budget.append(i + 2)
        #         continue

        #     # Checks for over threshold
        #     if self._string_to_float(consumed_list[i]) / self._string_to_float(total_list[i]) >= consumption_percentage_threshold:
        #         index_over_threshold.append(i + 2)

        # if len(indexes_over_budget) == 0:
        #     print("No projects over budget")

        # else:
        #     # Gets the project names of projects that are over budget
        #     # REVIEW include PO and quote as well?
        #     project_column_index = self.spreadsheet.find_col_by_heading("Project")

        #     print(f"There are {len(indexes_over_budget)} items over budget")
        #     over_budget_names = []
        #     for i in indexes_over_budget:
        #         over_budget_names.append(self.spreadsheet.sheet.cell(i, project_column_index))

        #     # FIXME DEBUG
        #     pprint(over_budget_names)

        # if len(index_over_threshold) == 0:
        #     print("No projects over threshold")

        # else:
        #     # Gets the project names of projects that are over the budget threshold
        #     # REVIEW include PO and quote as well?
        #     project_column_index = self.spreadsheet.find_col_by_heading("Project")

        #     print(f"There are {len(index_over_threshold)} items over the budget consumption threshold of {consumption_percentage_threshold}")
        #     over_threshold_names = []
        #     for i in index_over_threshold:
        #         over_threshold_names.append(self.spreadsheet.sheet.cell(i, project_column_index).value)

        #     # FIXME REMOVE DEBUG
        #     pprint(over_threshold_names)

    def _generate_warning_strings(
        self, warnings_list: list, warning_type: Warnings
    ) -> str:
        """
        Formats warning strings

        `warnings_list` is a list of projects
        """
        warning_strings = []
        for project in warnings_list:
            if warning_type == self.Warnings.OVER_BUDGET_THRESHOLD:
                # If generating warnings for over threshold case
                message = (
                    f"'{project[self.spreadsheet.Columns.PROJECT_NAME.value]}' "
                    f"has consumed {self._string_to_float(project[self.spreadsheet.Columns.PERCENTAGE_CONSUMED.value])}% "
                    f"of {project[self.spreadsheet.Columns.TOTAL_BUDGET.value]}. "
                    f"(PO: {project[self.spreadsheet.Columns.PO.value] if project[self.spreadsheet.Columns.PO.value] != '' else 'N/A'}, "
                    f"Quote: {project[self.spreadsheet.Columns.QUOTE.value] if project[self.spreadsheet.Columns.QUOTE.value] != '' else 'N/A'})"
                )

            elif warning_type == self.Warnings.DAYS_REMAINING:
                # If generating warnings for close to deadline
                message = (
                    f"'{project[self.spreadsheet.Columns.PROJECT_NAME.value]}' "
                    f"has only {project[self.spreadsheet.Columns.DAYS_REMAINING.value]} days until the end date of "
                    f"{project[self.spreadsheet.Columns.END_DATE_ESTIMATE.value]}. "
                    f"(PO: {project[self.spreadsheet.Columns.PO.value] if project[self.spreadsheet.Columns.PO.value] != '' else 'N/A'}, "
                    f"Quote: {project[self.spreadsheet.Columns.QUOTE.value] if project[self.spreadsheet.Columns.QUOTE.value] != '' else 'N/A'})"
                )

            else:
                raise Exception(f"{warning_type} isn't a valid warning type")

            # Appends the message to the return list
            warning_strings.append(message)

        # Adds the messages to the object's dictionary attribute
        if warning_type in self.warning_strings:
            self.warning_strings[warning_type].extend(warning_strings)
        else:
            self.warning_strings[warning_type] = warning_strings

        return warning_strings

    def _string_to_float(self, input_string: str) -> float:
        """
        Converts a string to float

        - Removes all characters except numbers and the decimal point
        """
        valid = []
        for char in input_string:
            if char.isnumeric() or char == ".":
                valid.append(char)

        return float("".join(valid))

    def send_alerts(self, all_warnings: dict):
        """
        Emails the warnings to the recipients

        `all_warnings` should be a dict with the keys being the warning types and the values being a list of warning strings
        """
        email_subject = "Autogenerated Budget Alerts"

        email_body = (
            f"The following warnings were generated from the budget spreadsheet:\n"
        )

        # Iterates through each warning type to group them in the email
        for warning_type, warnings in all_warnings.items():
            if warning_type not in self.Warnings:
                # Invalid warning type
                raise Exception(f"{warning_type} isn't a valid warning type")

            # Days remaining
            if warning_type == self.Warnings.DAYS_REMAINING:
                heading = f"Projects With Only {self.days_remaining_warn_threshold} Days Before Estimated End Date:"

            # Over budget threshold
            if warning_type == self.Warnings.OVER_BUDGET_THRESHOLD:
                heading = f"Projects Consuming Over {self.budget_warn_percentage * 100}% Budget:"

            # Prepends a dash to the start of every warning for formatting
            temp = [f"- {warning}" for warning in warnings]
            # Adds to the email body, the last empty string ensures another newline
            email_body = "\n".join([email_body, heading, *temp, ""])

        # Joins the emails together in a comma separate string
        recipients_string = ",".join(email for _, email in self.emails.items())
        # FIXME remove debug print
        print(email_subject)
        print(email_body)

        if not self.suppress_emails:
            if self.emails == {}:
                raise Exception("Couldn't send email, no recipients provided")

            XeroEmailSender.send_budget_alerts(
                recipients_string, email_subject, email_body
            )


if __name__ == "__main__":
    # TODO remove this when done
    if "CI" in os.environ:
        raise NotImplementedError("Spreadsheet functionality not complete")

    current_dir = os.path.dirname(os.path.realpath(__file__))

    parser = argparse.ArgumentParser("Update google spreadsheet report")
    parser.add_argument("--client-id", type=str, required=True)
    parser.add_argument("--client-secret", type=str, required=True)
    parser.add_argument("--refresh-token", type=str, required=True)
    parser.add_argument("--tenant-id", type=str, required=True)
    parser.add_argument("--url", type=str, required=True)
    parser.add_argument("--credential", type=str, required=True)
    parser.add_argument("--emails-file", type=str, required=False, default=None)

    parser.add_argument("--suppress-emails", type=bool, required=False, default=False)

    parser.add_argument("--budget-warn-percentage", type=float, required=True)
    parser.add_argument("--days-remaining-warn-threshold", type=int, required=True)

    args = parser.parse_args(sys.argv[1:])

    report = XeroSpreadSheetReport(args)
    report.sync()

    print("self.warning_strings:")
    pprint(report.warning_strings)
    exit()

    over_threshold_entries = report.check_budget_consumed()
    days_remaining_entries = report.check_remaining_days()

    # Generates warning strings from warnings
    warnings = {}
    warnings[report.Warnings.OVER_BUDGET_THRESHOLD] = report._generate_warning_strings(
        over_threshold_entries, report.Warnings.OVER_BUDGET_THRESHOLD
    )
    warnings[report.Warnings.DAYS_REMAINING] = report._generate_warning_strings(
        days_remaining_entries, report.Warnings.DAYS_REMAINING
    )

    report.send_alerts(warnings)

    sys.exit(0)
