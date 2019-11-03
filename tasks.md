# Xero Automation Tasks

- Add menu option to create time-sheets of the month.
    - No parameter means this month.
    - Start and end date should be all encompassing. This is to include entries with the wrong date.
    - Failure, with failure report if there is a wrong date.
    - Add validations. Full time employees should max-out hours for the month.

-Generate Excel Spreadsheet for SNSW.

-Create time-sheets of a particular month.

-Export all time-sheets.
    -Mandatory: Specify time period.

-Run validations.
    -Generate a report and email it to employee and admin@darumatic.com
    -Validate that the time date belongs to the right month.
    -Validate that the projects are including a valid month.
    -Warning in case there are more than 40 hours per consultant, per project, per month.

-Generate Budget report.
    -Update the Spreadsheet.
    -Email to recipients.

-Option to store reports in Google Drive.

-Refactor code, like removing unused main options.

-Duplicate projects automatically.

-Close projects automatically.

-Remind people to enter their time-sheets monthly.
