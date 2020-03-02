# Xero Automation

The project generates Xero Project Time report. 


## How to use it? 

```
python xero_report.py --start_time=2020-04-01 --end_time=2020-04-30 --client_id=3D91BDB5880A4ECEA2F179CCD8534844 --client_secret="lhJ799NYGzd9PCDq_0neN5dSHncevHjij2nwvk6vsn7GQq9_"
```

> NOTE: When create the Xero project, the callback URL should be http://localhost:3000

When first time to run the script, the script will output a oauth URL, need to manually 
open that URL in browser. The script handles the callback and create a config file in current user home folder. 


For example: xero-3D91BDB5880A4ECEA2F179CCD8534844.json
```
{"tenant_id": "f2384ce5-58aa-4838-a67a-807340bab535", "refresh_token": "12bc96eecb2f4b220b37757ddda9b8b5939a9198862ea49ad0c5dab0f4361155", "client_id": "3D91BDB5880A4ECEA2F179CCD8534844"}

```