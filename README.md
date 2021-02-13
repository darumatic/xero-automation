# Xero Automation

This project automates tasks in Xero.

## How to run this project (on your local machine):

### Getting Tokens

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

### Validating Report

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


### Generating and Exporting Report
This will generate a PDF and XLS of the timesheet for a Xero project named `YYYYmm`, where `mm` is the previous month from today. For example, running this in January 2021 will generate a timesheet for project `202012`, and running this in Feburary 2021 will generate a PDF for project `202101`. The report will be sent as an email but this can be suppressed.

1. Edit `scripts/run_report.sh`:
	- Replace `--refresh-token` and `--tenant-id` with the values you got [from before](###Getting-Tokens).
	- Add `--skip-owners=True` if there aren't any owner data for the projects.
	- Add `--suppress-email=True` if you don't want it emailing the final report. For emailing to work on your local machine, you'll need to set up environmental variables. See [Note about emailing](#Note-about-emailing).
2. (Optional) To change the month/project to generate a timesheet for, specify it in the environmental variable `$PROJECT_NAME`. For example, set it to `202012` to generate a timesheet for that project.
3. Run `scripts/run_report.sh`.
4. Check the `out` folder for the output.
## Run with Gitlab pipeline

Add the following CI/CD variables:

- `$COMMAND`: validate | report
- `$CLIENT_ID`: Xero app client id
- `$CLIENT_SECRET`: Xero app client secret
- `$GITLAB_PRIVATE_TOKEN`: Gitlab personal private token, check document on the next section.
- `$REFRESH_TOKEN`: Xero refresh token, result of get_refresh_token.py
- `$TENANT_ID`: Xero tenant id, result of get_refresh_token.py
- `$OWNERS`: Dictionary with Project name and contacts. Example: `{ 'Project A': 'Neil', 'Non chargeable tasks': 'Adrian' }` (optional if `--skip-owners=True`)
- `$VALIDATION_EXCEPTIONS`: Python list with time entries with tasks ids that need to be skipped. Example: `['task_id1', 'task_id1']` (optional)
- `$PROJECT_NAME`: month/project to generate a timesheet for (optional, defaults to last month)
- `$LOCAL_TIMEZONE`: local timezone of the data. A string from the `TZ Database Name` column from [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) (optional, defaults to `Australia/Sydney`)

Default start time is the first day of the current month and end time is the last day of the current month.

### How to create GITLAB_PRIVATE_TOKEN?

Xero refresh token expired after we retrieve access token, so we need to update REFRESH_TOKEN for each pipeline execution.

- Open https://gitlab.com/profile/personal_access_tokens
- select api scope
- Click "Create Personal access token"

### `run-report`
When run on GitLab, this job will also push the report to another repo on top of sending it as an email.


## How it works (Oauth 2)?

- Xero expires refresh token after retrieving access token
- For pipeline, we use gitlab API to update CI/CD variable REFRESH_TOKEN to keep the refresh token updated.

### What to do if the GitLab runner fails to retrieve tokens from Xero

1. On your local machine, run `scripts/get_tokens.sh` but replace the `--client-id` and `--client-secret` with the one the GitLab runner is using. You can get that from GitLab in `Settings > CI / CD > Variables`.

2. Login and make sure the app has access to `Darumatic Pty Ltd`.

3. Check the terminal and replace the GitLab runner's variables `$REFRESH_TOKEN` and `$TENANT_ID` with the one you just got.

## Note about emailing

The sender, recipient, and API key are stored in environmental variables `$SENDER`, `$RECEIVER`, and `$SENDGRID_API_KEY` respectively. The GitLab CI script gets those variables from [this repo](https://gitlab.com/xero-automation-prod/xero-configuration) before running the program. If these environmental variables aren't present, emails are suppressed anyway to prevent an exception.
