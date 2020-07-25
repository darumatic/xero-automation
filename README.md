# Xero Automation

This project automates tasks in Xero. 


## How to run this project:

- In https://developer.xero.com/ create a Xero app, and get its client id and secret. 

- Get the Xero tenant ID and refresh token. 

```bash

python get_refresh_token.py --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g
```

- Copy the URL from command line and open it with a local browser
```bash
root@DESKTOP-GGSPFA4:~/Workspace/darumatic/xero-automation# python get_refresh_token.py --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g
Please open the following URL in your browser:
https://login.xero.com/identity/connect/authorize?response_type=code&client_id=4C1C814C07D34E3C8F1351A31497095D&redirect_uri=http%3A%2F%2Flocalhost%3A3000&scope=offline_access+projects+openid+accounting.contacts&state=xEcAFRp1I7wuRmCOM8lAlkTEf8G7RX&prompt=select_account&access_type=offline
TENANT_ID:e2860eff-e674-4d3e-9001-8affbd5f40a7
```
- Login Xero and grant access to Xero App.
- Get Xero tenant id and refresh token from console output

- Run command
```bash
python xero_report.py validate --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g 
--refresh-token=7daf4a7abb77de35e08fa0efbbd8f7a479ba5e39fc3ca4fed01f63585329b94c --tenant-id=e2860eff-e674-4d3e-9001-8affbd5f40a7
--start-time=xxx --end-time=xxx
```

## Run with Gitlab pipeline

Add the following CI/CD variables:

- COMMAND: validate | report
- CLIENT_ID: Xero app client id
- CLIENT_SECRET: Xero app client secret
- GITLAB_PRIVATE_TOKEN: Gitlab personal private token, check document on the next section.
- REFRESH_TOKEN: Xero refresh token, result of get_refresh_token.py
- TENANT_ID: Xero tenant id, result of get_refresh_token.py
- OWNERS: Dictionary with Project name and contacts. Example: "{ 'Project A': 'Neil', 'Non chargeable tasks': 'Adrian' }"
- VALIDATION_EXCEPTIONS: Python list with time entries with taks ids that need to be skipped. Example: "['task_id1', 'task_id1']"


Default start time is the first day of the current month and end time is the last day of the current month.

### How to create GITLAB_PRIVATE_TOKEN? 

Xero refresh token expired after we retrieve access token, so we need to update REFRESH_TOKEN for each pipeline execution.  

- Open https://gitlab.com/profile/personal_access_tokens
- select api scope
- Click "Create Personal access token"


## How it works? 

- Xero expires refresh token after retrieving access token
- For pipeline, we use gitlab API to update CI/CD variable REFRESH_TOKEN to keep the refresh token updated. 
 
