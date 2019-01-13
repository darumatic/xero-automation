# Xero Automation

The project generates Xero Project Time report. 


## Manual run the command 

```
./xero_report.sh --PROJECT_ID=fa6649e7-f55d-40bb-8a31-55cf2fb18d5c --START_DATE=2018-12-01 --END_DATE=2018-12-30 --XERO_CONSUMER_KEY=RC0JPAB2DPT71YLTXHBVP6AWJFV73W --XERO_PRIVATE_KEY_FILE=./rsa_key.pem
```

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
  
## Run with Gitlab pipeline

Generate Xero report and upload report PDF to the remote git repo. Demo repository https://gitlab.com/snsw-int/xero-report. 

CI/CD variables: 
- PROJECT_ID
  
  Same as above.
  
- XERO_CONSUMER_KEY
  
  Same as above.
  
- XERO_PRIVATE_KEY

  XERO_PRIVATE_KEY is Xero private APP RSA private key content.
  
- DURATION_WEEKS
  
  For Gitlab CRON schedule, we could not specify START_DATE. So we use END_DATE to be current week's SUNDAY, START_DATE is set to be END_DATE - DURATION_WEEKS * 7.

- SSH_PRIVATE_KEY

  Gitlab deployment private key to push report files to remote git repo.
  
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
  