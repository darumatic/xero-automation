# Xero Automation

The project generates Xero Project Time report. 


## Manual run the command 

```
example usages:

to clone projects
python main.py --start-date 2019-10-01 --end-date 2019-10-31 --consumer-key KSBYNZLKTG5KZXWTFJZANB3R4ZYBH9 --private-key-file privatekey.pem --run-mode clone-projects

to generate timesheets for all weeks and also send an email run with these params
python main.py --start-date 2019-11-01 --end-date 2019-11-30 --consumer-key KSBYNZLKTG5KZXWTFJZANB3R4ZYBH9 --private-key-file privatekey.pem --run-mode excel-reports-timesheet

```
known issue: currently the dates are not used correctly in all cases.

run --help to obtain information about parameters
python main.py --help 


- PROJECT_ID
  
  PROJECT_ID is the Xero project id. We can get it from URL, like https://projects.xero.com/project/**f91ae7a1-df8c-41e6-9602-e45d11842425**/
  Multi project ids are separated by ','.
  
- START_DATE
 
  START_DATE is the report start date. The date format is yyyy-MM-dd.
  
- END_DATE

  END_DATE is the report start date. The END_DATE is included in the report.
  
- XERO_CONSUMER_KEY

  XERO_CONSUMER_KEY is Xero private app consumer key. See 
  
- XERO_PRIVATE_KEY_FILE

  XERO_PRIVATE_KEY_FILE is Xero private app RSA private key file path.

- RUN-MODE
  the program logic that you want to run from a list of predefined actions, run the tool with --help to see the possible values


## Run with Gitlab pipeline

Generate Xero report and upload report PDF to the remote git repo. Demo repository https://gitlab.com/snsw-int/xero-report. 

CI/CD variables: 

  
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
