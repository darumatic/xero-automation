# Xero Automation

This project automates tasks in Xero. It:

- performs validation on the employee hours
- generates monthly timesheets
- manually generates timesheets by PO
- closes old projects.

<!-- ## How to run this project (on your local machine) -->

## Getting Tokens

- In https://developer.xero.com/ create a Xero app, and get its client id and secret.

- Get the Xero tenant ID and refresh token.

- Run
	```bash
	python get_refresh_token.py --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g
	```
	or use `scripts/get_tokens.sh`

- Copy the URL from command line and open it with a local browser

	```bash
	root@DESKTOP-GGSPFA4:~/Workspace/darumatic/xero-automation# python get_refresh_token.py --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g
	Please open the following URL in your browser:
	https://login.xero.com/identity/connect/authorize?response_type=code&client_id=4C1C814C07D34E3C8F1351A31497095D&redirect_uri=http%3A%2F%2Flocalhost%3A3000&scope=offline_access+projects+openid+accounting.contacts&state=xEcAFRp1I7wuRmCOM8lAlkTEf8G7RX&prompt=select_account&access_type=offline
	TENANT_ID:e2860eff-e674-4d3e-9001-8affbd5f40a7
	```
- Login Xero and grant access to Xero App.
- Get Xero tenant id and refresh token from console output

## Validating Report (`validate`)

#### Running Locally

Run command
```bash
python xero_report.py validate \
--client-id=4C1C814C07D34E3C8F1351A31497095D \
--client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g \
--refresh-token=<TOKEN_GOES_HERE> \
--tenant-id=<TENANT_ID_GOES_HERE> \
--start-time=<START_TIME_GOES_HERE> \
--end-time=<END_TIME_GOES_HERE>
```
where
- `--refresh-token` and `--tenant-id` are values you got [from before](###Getting-Tokens),
- `--start-time` and `--end-time` define the period to look for tasks to validate. These should be in the format `YYYY-mm-dd` (e.g. `2021-01-02` for the 2nd of January, 2021). These values are optional and default to the the first and last day of the current month.

### Running on GitLab

Add the following CI/CD variables:

- `$COMMAND`: validate | report
- `$CLIENT_ID`: Xero app client id
- `$CLIENT_SECRET`: Xero app client secret
- `$GITLAB_PRIVATE_TOKEN`: Gitlab personal private token, see [here](###How-to-create-GITLAB_PRIVATE_TOKEN?).
- `$REFRESH_TOKEN`: Xero refresh token, result of get_refresh_token.py
- `$TENANT_ID`: Xero tenant id, result of get_refresh_token.py
- `$OWNERS`: Dictionary with Project name and contacts. Example: `{ 'Project A': 'Neil', 'Non chargeable tasks': 'Adrian' }` (optional if `--skip-owners=True`)
- `$VALIDATION_EXCEPTIONS`: Python list with time entries with tasks ids that need to be skipped. Example: `['task_id1', 'task_id1']` (optional)
<!-- - `$PROJECT_NAME`: month/project to generate a timesheet for (optional, defaults to last month) -->
- `$LOCAL_TIMEZONE`: local timezone of the data. A string from the `TZ Database Name` column from [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) (optional, defaults to `Australia/Sydney`)

## Generating Monthly Timesheet (`report-month`)

This will generate a PDF and XLS of the timesheet for a Xero project named `YYYYmm`, where `mm` is the previous month from today. For example, running this in January 2021 will generate a timesheet for project `202012`, and running this in Feburary 2021 will generate a PDF for project `202101`. The report will be sent as an email but this can be suppressed.

### Running Locally

1. Edit `scripts/report-month.sh`:
	- Replace `--refresh-token` and `--tenant-id` with the values you got [from before](##Getting-Tokens).
	- Add `--skip-owners=True` if there aren't any owner data for the projects.
	- Add `--suppress-email=True` if you don't want it emailing the final report. For emailing to work on your local machine, you'll need to set up environmental variables. See [Note about emailing](#Note-about-emailing).
2. (Optional) To change the month/project to generate a timesheet for, specify it in the environmental variable `$PROJECT_NAME`. For example, set it to `202012` to generate a timesheet for that project.
3. Run `scripts/report-month.sh`.
4. Check the `out` folder for the output.

### Running on GitLab

On GitLab, it will pull the configuration repo for email details. It will also push the generated documents to the `xero-reports` repo.

Add the following CI/CD variables:

<!-- - `$COMMAND`: validate | report -->
- `$CLIENT_ID`: Xero app client id
- `$CLIENT_SECRET`: Xero app client secret
- `$GITLAB_PRIVATE_TOKEN`: Gitlab personal private token, check document on the next section.
- `$REFRESH_TOKEN`: Xero refresh token, result of get_refresh_token.py
- `$TENANT_ID`: Xero tenant id, result of get_refresh_token.py
- (Optional when `--skip-owners=True`) `$OWNERS`: Dictionary with Project name and contacts. Example:
	```json
		{ 'Project A': 'Neil', 'Non chargeable tasks': 'Adrian' }
	```
- (Optional) `$PROJECT_NAME`: month/project to generate a timesheet for (defaults to last month)
- (Optional) `$LOCAL_TIMEZONE`: local timezone of the data. A string from the `TZ Database Name` column from [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) (defaults to `Australia/Sydney`)

## Generating Timesheet by PO (`report-po`)

This will generate a PDF and XLS for all projects with a specified PO within a time range. E.g. setting `--po=12345` will look for all projects with `PO 12345` in its name between `--start-time` and `--end-time`. The start time defaults to 2017-02-01 and end time to now.
### Running Locally

1. Edit `scripts/report-po.sh`:
	- Replace `--refresh-token` and `--tenant-id` with the values you got [from before](##Getting-Tokens).
	- Add `--skip-owners=True` if there aren't any owner data for the projects.
	- Add `--suppress-email=True` if you don't want it emailing the final report. For emailing to work on your local machine, you'll need to set up environmental variables. See [Note about emailing](#Note-about-emailing).
	- Add `--po=XXXXXXXX` for the PO to generate the timesheet for

2. (Optional) Specify the date range with `--start-time=YYYY-mm-dd` and `--end-time=YYYY-mm-dd`. It defaults to 2017-02-01 for start and now for end.

3. Run `scripts/report-po.sh`.
4. Check the `out` folder for the output

### Running on GItLab

On GitLab, it will pull the configuration repo for email details. It will also push the generated documents to the `xero-reports` repo.

Add the following CI/CD variables:

- `$CLIENT_ID`: Xero app client id
- `$CLIENT_SECRET`: Xero app client secret
- `$GITLAB_PRIVATE_TOKEN`: Gitlab personal private token, check document on the next section.
- `$REFRESH_TOKEN`: Xero refresh token, result of get_refresh_token.py
- `$TENANT_ID`: Xero tenant id, result of get_refresh_token.py
- `$PO`: PO to generate the report for
- (Optional) `$START_TIME`: See below, defaults to 2017-02-01
- (Optional) `$END_TIME`: Time ranges to generate the timesheet for, defaults to now
- (Optional when `--skip-owners=True`) `$OWNERS`: Dictionary with Project name and contacts. Example:
	```json
		{ 'Project A': 'Neil', 'Non chargeable tasks': 'Adrian' }
	```
- (Optional) `$LOCAL_TIMEZONE`: local timezone of the data. A string from the `TZ Database Name` column from [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) (defaults to `Australia/Sydney`)

<!-- TODO uncomment when ready -->
<!-- # xero_spread_sheet_report.py

## 1. Run xero_spread_sheet_report.py command

1. In https://developer.xero.com/ create a Xero app, and get its client id and secret.
2. Get the Xero tenant ID and refresh token.
    ```bash
    python get_refresh_token.py --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g
    ```
3. Copy the URL from command line and open it with a local browser
    ```bash
    root@DESKTOP-GGSPFA4:~/Workspace/darumatic/xero-automation# python get_refresh_token.py --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g
    Please open the following URL in your browser:
    https://login.xero.com/identity/connect/authorize?response_type=code&client_id=4C1C814C07D34E3C8F1351A31497095D&redirect_uri=http%3A%2F%2Flocalhost%3A3000&scope=offline_access+projects+openid+accounting.contacts&state=xEcAFRp1I7wuRmCOM8lAlkTEf8G7RX&prompt=select_account&access_type=offline
    TENANT_ID:e2860eff-e674-4d3e-9001-8affbd5f40a7
    ```
4. Login Xero and grant access to Xero App.

5. Get Xero tenant id and refresh token from console output


6. Enable Google Sheets and Driver API
   Open google cloud console. https://console.cloud.google.com/, click Home > API & Services > Libraries. Search the following services and make sure they are both enabled.
   - Google Sheets API
   - Google Drive API

7. Create service account
   Home > API & Services > Credentials > Manage Service Account. In the service account management page, create an new service account.

8. Download service account key file.
   Select the service account in the service account management page. In the detail page, click [Add Key]>[Create new Key], then select JSON key type, then click [Create], the key file would be downloaded automatically.

9. Share the spreadsheet to service account
    Open the target spreadsheet page. Click [Share] button, share the spreadsheet with **write** permission to the service account email.

10. Run command
    ```bash
    python xero_spread_sheet_report.py --client-id=AAC4378034054ED7A23908B5A558B695
    --client-secret=Bjc9KFHUE1Fmj-5cQ57CbQiMOWmguyFff4j7nvFGaOfqXOeH
    --tenant-id=f9e1ecae-d6fd-4275-8a33-bd1c918b466b
    --refresh-token=2d1ddb791bbe9ec4e93f813b4f2a3aeeeddc528aa44eb0bfe26e563f77146f62
    --credential=advance-vector-300706-b26103bcdb8b.json
    --url=https://docs.google.com/spreadsheets/d/1G6ZOc1BYok0w5W6lZQB-GK92mfWgCLtVhXuNlBM-xyU
    ```

Example output:
```bash
Updated 2 projects:
- 202012 - Anand Covid Safe Check In - PO 45477812 update budget consumed to be 640.0
- Test Project3 PO 45477814 update budget consumed to be 0.0

There are 2 warnings:
- 202012 - DLP Sarel - QU 201008
  Invalid project name format, missing PO
- Xero deleted project
  Cant find project in Xero

``` -->
## How to create GITLAB_PRIVATE_TOKEN?

Xero refresh token expired after we retrieve access token, so we need to update REFRESH_TOKEN for each pipeline execution.

- Open https://gitlab.com/profile/personal_access_tokens
- select api scope
- Click "Create Personal access token"

### `run-report`

When run on GitLab, this job will also push the report to the reports repo ([UAT](https://gitlab.com/darumatic/xero-automation-uat/xero-report), [PROD](https://gitlab.com/xero-automation-prod/xero-reports)) on top of sending it as an email.

## How it works (Oauth 2)?

- Xero expires refresh token after retrieving access token
- For pipeline, we use gitlab API to update CI/CD variable REFRESH_TOKEN to keep the refresh token updated.

### What to do if the GitLab runner fails to retrieve tokens from Xero

1. On your local machine, run `scripts/get_tokens.sh` but replace the `--client-id` and `--client-secret` with the one the GitLab runner is using. You can get that from GitLab in `Settings > CI / CD > Variables`.

2. Login and make sure the app has access to `Darumatic Pty Ltd`.

3. Check the terminal and replace the GitLab runner's variables `$REFRESH_TOKEN` and `$TENANT_ID` with the one you just got.

## Note about emailing

The sender, recipient, and API key are stored in environmental variables `$SENDER`, `$RECEIVER`, and `$SENDGRID_API_KEY` respectively. The GitLab CI script gets those variables from the configuration repo ([UAT](https://gitlab.com/darumatic/xero-automation-uat/xero-configuration), [PROD](https://gitlab.com/xero-automation-prod/xero-configuration)) before running the program. If these environmental variables aren't present, emails are suppressed anyway to prevent an exception.
