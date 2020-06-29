# Xero Automation

The project generates Xero Project Time report. 


## Manual run the command 

- Get Xero tenant ID and refresh token

```bash

python get_refresh_token.py --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g
```
> For client id and secret, refer to "How to create a Xero APP"
- Copy the URL from command line and open with local browser
```bash
root@DESKTOP-GGSPFA4:~/Workspace/darumatic/xero-automation# python get_refresh_token.py --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g
Please open the following URL in your browser:
https://login.xero.com/identity/connect/authorize?response_type=code&client_id=4C1C814C07D34E3C8F1351A31497095D&redirect_uri=http%3A%2F%2Flocalhost%3A3000&scope=offline_access+projects+openid+accounting.contacts&state=xEcAFRp1I7wuRmCOM8lAlkTEf8G7RX&prompt=select_account&access_type=offline
TENANT_ID:e2860eff-e674-4d3e-9001-8affbd5f40a7
```
- Login Xero 
- Get Xero tenant id and refresh token from console output


- Run validation
```bash
python xero_report.py validate --client-id=4C1C814C07D34E3C8F1351A31497095D --client-secret=zx5QB1reXAW0VW-AaCcK4kjjUO1dLfDR0gb9_VoD592XCP8g 
--refresh-token=7daf4a7abb77de35e08fa0efbbd8f7a479ba5e39fc3ca4fed01f63585329b94c --tenant-id=e2860eff-e674-4d3e-9001-8affbd5f40a7
--start-time=xxx --end-time=xxx
```

## Run with Gitlab pipeline

Add the following CI/CD variable:

- COMMAND: validate
- CLIENT_ID
- CLIENT_SECRET
- GITLAB_PRIVATE_TOKEN 
- REFRESH_TOKEN
- TENANT_ID

Default start time is the first day of the current month and end time is the last day.

### How to create GITLAB_PRIVATE_TOKEN? 

Xero refresh token expired after we retrieve access token, so we need to update REFRESH_TOKEN for each pipeline execution.  

- Open https://gitlab.com/profile/personal_access_tokens
- select api scope
- Click "Create Personal access token"
  

## How to create a Xero APP

1. Open https://developer.xero.com/myapps/
2. Click [New App].
3. Select private app.
4. Input app name and select organization.
5. Create cert. https://developer.xero.com/documentation/api-guides/create-publicprivate-key

    ```
    openssl genrsa -out privatekey.pem 1024
    openssl req -new -x509 -key privatekey.pem -out publickey.cer -days 1825
    openssl pkcs12 -export -out public_privatekey.pfx -inkey privatekey.pem -in publickey.cer
    ```
6. Upload publickey.cer.
7. XERO_CONSUMER_KEY is OAuth 1.0a Credentials Consumer Key.
8. XERO_PRIVATE_KEY is privatekey.pem content.
