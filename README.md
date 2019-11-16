# ./elastalerter.py

## ENVIRONMENT

<table>
<tr>
	<td><strong>ELASTICSEARCH</strong></td>
	<td><a href="https://www.elastic.co/downloads/past-releases/elasticsearch-7-4-0">v7.4.0</a></td>
</tr>
<tr>
	<td><strong>VIRTUAL ENVIRONMENT</strong></td>
	<td>Python 3.6</td>
</tr>
<tr>
	<td><strong>OPERATING SYSTEM</strong></td>
	<td>Linux (in this case: Ubuntu 18.04)</td>
</tr>
</table>

---

## IMPORTANT NOTES

- This probably <span style="color:red">__won't work__</span> on Windows Machines.
- The program manually creates a basic config file if none is specified.
- The program manually sets the rule's alert to __`elastalerter.alerter.Alert`__.
- If mappings are not specified during aggregation, key fields are __automatically set as keyword fields__:
  ```yaml
  query_key: field_name.keyword
  metric_agg_key: field_name.keyword
  ```
- Logs to be used in a specific test could be a list of files or a directory containing all logs to be indexed.
  ```json
  "log": ["log1.json", "log2.json", ...]
  
   or

  "log": "/dir"
  ```
- If a directory is specified, the program will check if it exists as is, in the directory specified in __`--logs`__, or in the current working directory.
- Test results are laid out as follows in __`results.json`__:
  ```json
  {
      "total": 6,
      "pass": 3,
      "fail": 3,
      "tests": {
          "test_2": {
              "result": "PASSED",
              "message": []
          },
          "test_2": {
              "result": "PASSED",
              "message": []
          },
          "test_3": {
              "result": "FAILED",
              "message": [
                  "1 LOG(S) MATCHED: log001.json"
              ]
          },
          "test_4": {
              "result": "FAILED",
              "message": [
                  "7 LOG(S) DID NOT MATCH: agg_log001.json, agg_log002.json, agg_log003.json, agg_log004.json, agg_log005.json, log001.json, log003.json"
              ]
          },
          "test_agg_1": {
              "result": "FAILED",
              "message": [
                  "HITS (5) EXCEEDED THE THRESHOLD"
              ]
          }
      }
  }
  ```

---

## SET-UP

1. Download and run [elasticsearch 7.4.0](https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-7.4.0-linux-x86_64.tar.gz) for Linux.

   ```console
   $ tar xvf elasticsearch-7.4.0-linux-x86_64.tar.gz

     ...

   $ elasticsearch-7.4.0/bin/elasticsearch

     ...

   ```

2. Set-up a python virtual environment:

   ```console
   $ pip3 install virtualenv

   $ python3 -m virtualenv v_env

     Using base prefix '/usr'
     New python executable in CURRENT_WORKING_DIRECTORY/v_env/bin/python3
     Also creating executable in CURRENT_WORKING_DIRECTORY/v_env/bin/python
     Installing setuptools, pip, wheel...
     done.

   $ source v_env/bin/activate

   (v_env) $
   ```

3. Download and install dependencies for __*elastalerter.py*__

   ```console
   (v_env) $ wget https://github.com/jebidiah-anthony/elastalerter/blob/master/elastalerter.zip?raw=true
   ```
   ```
     ...omitted...
     HTTP request sent, awaiting response... 200 OK
     Length: 4248 (4.1K) [application/zip]
     Saving to: ‘elastalerter.zip’

     elastalerter.zip         100%[================================>]   4.15K  --.-KB/s    in 0s
     ...omitted...
   ```
   ```console
   (v_env) $ unzip elastalerter.py 
   ```
   ```
     Archive:  elastalerter.zip
       inflating: elastalerter.py
       inflating: requirements.txt
       inflating: setup.py 
   ```
   ```console
   (v_env) $ pip install --requirement requirements.txt
   ```
   ```
     ...omitted...
     Installing collected packages: pytz, tzlocal, six, APScheduler, urllib3, idna, certifi, chardet, requests, 
     aws-requests-auth, blist, docutils, jmespath, python-dateutil, botocore, s3transfer, boto3, pycparser, cffi, 
     configparser, croniter, defusedxml, docopt, jsonschema, mock, PyStaticConfiguration, stomp.py, exotel, 
     envparse, python-magic, pbr, oauthlib, requests-oauthlib, requests-toolbelt, jira, PyYAML, PySocks, PyJWT, 
     twilio, texttable, elasticsearch, future, thehive4py, elastalert, tabulate
     ...omitted...
   ```
   ```console
   (v_env) $ pip install .
   ```
   ```
     ...omitted...
     Successfully built elastalerter
     Installing collected packages: elastalerter
     Successfully installed elastalerter-0.0.1
   ```

---

## EXECUTION (w/ sample output)

### help (__`-h, --help`__)
```console
(v_env) $ python elastalerter.py -h
```
```
usage: python ./elastalerter.py --logs LOGS_DIR --rules RULES_DIR --expected expected.json

    SAMPLE "expected.json"
    ------------------------------------------------
    {
        "test_1": {
            "rule": "rule.yaml",
            "log": ["log1.json", "log2.json", ...],
            "match": (true | false),
            "enabled": (true | false)
        },
        "test_2": {
            ...
            "log": "/dir"
            ...
        },
        ...
    }

optional arguments:
  -h, --help       show this help message and exit
  --host HOST      elasticsearch instance host address (default: 127.0.0.1)
  --port PORT      elasticsearch instance port (default: 9200)
  --config YAML    elastalert config file to use.
  --mappings JSON  field data type mappings.
  --verbose        output other details

required arguments:
  --expected JSON  JSON outline of test names and expected results
  --logs DIR       directory of the logs to be indexed
  --rules DIR      directory of the rules to run with elastalert
```

### default output
```console
(v_env) $ python elastalerter.py --logs ./logs --rules ./rules --expected expected.json
```
```
[+] RUNNING test_1 :
    [+] TESTING RULE -- RULE01 ( ./rule01.yaml )
    [+] TEST ( test_1 ) PASSED

[+] RUNNING test_2 :
    [+] TESTING RULE -- RULE02 ( ./rule02.yaml )
    [+] TEST ( test_2 ) PASSED

[+] RUNNING test_3 :
    [+] TESTING RULE -- RULE01 ( ./rule01.yaml )
    [+] TEST ( test_3 ) FAILED

[+] RUNNING test_4 :
    [+] SPECIFIED LOGS IS A DIRECTORY ( ./logs )
        [ERROR] "test_file" IS NOT A VALID JSON FILE.
        [ERROR] "test_file.json" IS NOT A VALID LOG FILE.
    [+] TESTING RULE -- RULE02 ( ./rule02.yaml )
    [+] TEST ( test_4 ) FAILED

[+] RUNNING test_agg_1 :
    [+] TESTING RULE -- AGG_RULE01 ( ./agg_rule01.yaml )
    [+] TEST ( test_agg_1 ) FAILED

[+] RUNNING test_agg_02 :
    [+] TEST ( test_agg_2 ) WAS DISABLED


[+] RESULTS WERE OUTPUT TO CURRENT_WORKING_DIRECTORY/results.json

    ╒════════════╤══════════╤═════════════════════════════════════════════════════════════╕
    │ TestID     │ RESULT   │ MESSAGE                                                     │
    ╞════════════╪══════════╪═════════════════════════════════════════════════════════════╡
    │ test_1     │ PASSED   │                                                             │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_2     │ PASSED   │                                                             │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_3     │ FAILED   │ > 1 LOG(S) MATCHED: log001.json                             │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_4     │ FAILED   │ > 7 LOG(S) DID NOT MATCH: agg_log001.json, agg_log002.json, │
    │            │          │   agg_log003.json, agg_log004.json, agg_log005.json,        │
    │            │          │   log001.json, log003.json                                  │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_agg_1 │ FAILED   │ > NO LOG(S) MATCHED.                                        │
    ╘════════════╧══════════╧═════════════════════════════════════════════════════════════╛
```

### mappings (__`--mappings`__)

#### > sample mappings.json
```json
{
    "mappings": {
        "properties": {
            "ip": { "type": "ip" },
            "port": { "type": "integer" }
        }
    }
}
```

#### > execution
```console
(v_env) $ python elastalerter.py --logs ./logs --rules ./rules --expected expected.json --mappings mappings.json
```
```
[+] RUNNING test_1 :
    [+] TESTING RULE -- RULE01 ( ./rule01.yaml )
    [+] TEST ( test_1 ) PASSED

[+] RUNNING test_2 :
    [+] TESTING RULE -- RULE02 ( ./rule02.yaml )
    [+] TEST ( test_2 ) PASSED

[+] RUNNING test_3 :
    [+] TESTING RULE -- RULE01 ( ./rule01.yaml )
    [+] TEST ( test_3 ) FAILED

[+] RUNNING test_4 :
    [+] SPECIFIED LOGS IS A DIRECTORY ( ./logs )
        [ERROR] "test_file" IS NOT A VALID JSON FILE.
        [ERROR] "test_file.json" IS NOT A VALID LOG FILE.
    [+] TESTING RULE -- RULE02 ( ./rule02.yaml )
    [+] TEST ( test_4 ) FAILED

[+] RUNNING test_agg_1 :
    [+] TESTING RULE -- AGG_RULE01 ( ./agg_rule01.yaml )
    [+] TEST ( test_agg_1 ) FAILED

[+] RUNNING test_agg_02 :
    [+] TEST ( test_agg_2 ) WAS DISABLED


[+] RESULTS WERE OUTPUT TO CURRENT_WORKING_DIRECTORY/results.json

    ╒════════════╤══════════╤═════════════════════════════════════════════════════════════╕
    │ TestID     │ RESULT   │ MESSAGE                                                     │
    ╞════════════╪══════════╪═════════════════════════════════════════════════════════════╡
    │ test_1     │ PASSED   │                                                             │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_2     │ PASSED   │                                                             │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_3     │ FAILED   │ > 1 LOG(S) MATCHED: log001.json                             │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_4     │ FAILED   │ > 7 LOG(S) DID NOT MATCH: agg_log001.json, agg_log002.json, │
    │            │          │   agg_log003.json, agg_log004.json, agg_log005.json,        │
    │            │          │   log001.json, log003.json                                  │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_agg_1 │ FAILED   │ > HITS (5) EXCEEDED THE THRESHOLD                           │
    ╘════════════╧══════════╧═════════════════════════════════════════════════════════════╛
```

### verbose (__`--verbose`__)
```console
(v_env) $ python elastalerter.py --logs ./logs --rules ./rules --expected ./expected.json --verbose
```
```
[+] RUNNING test_1 :
    [+] A NEW INDEX ( test_1 ) WAS CREATED
    [+] TIMESTAMP RANGE -- [2019-09-16T15:59:57 - 2019-09-16T15:59:57]
    [+] TESTING RULE -- RULE01 ( ./rule01.yaml )
    [+] UPDATING RESULTS...
    [+] DELETING TEST INDEX...
    [+] TEST ( test_1 ) PASSED

[+] RUNNING test_2 :
    [+] A NEW INDEX ( test_2 ) WAS CREATED
    [+] TIMESTAMP RANGE -- [2019-09-16T15:59:57 - 2019-09-16T15:59:57]
    [+] TESTING RULE -- RULE02 ( ./rule02.yaml )
    [+] UPDATING RESULTS...
    [+] DELETING TEST INDEX...
    [+] TEST ( test_2 ) PASSED

[+] RUNNING test_3 :
    [+] A NEW INDEX ( test_3 ) WAS CREATED
    [+] TIMESTAMP RANGE -- [2019-09-16T15:59:57 - 2019-09-16T15:59:57]
    [+] TESTING RULE -- RULE01 ( ./rule01.yaml )
    [+] UPDATING RESULTS...
    [+] DELETING TEST INDEX...
    [+] TEST ( test_3 ) FAILED

[+] RUNNING test_4 :
    [+] A NEW INDEX ( test_4 ) WAS CREATED
    [+] SPECIFIED LOGS IS A DIRECTORY ( ./logs )
        [ERROR] "test_file" IS NOT A VALID JSON FILE.
        [ERROR] "test_file.json" IS NOT A VALID LOG FILE.
    [+] TIMESTAMP RANGE -- [2019-09-16T15:59:57 - 2019-09-16T15:59:57]
    [+] TESTING RULE -- RULE02 ( ./rule02.yaml )
    [+] UPDATING RESULTS...
    [+] DELETING TEST INDEX...
    [+] TEST ( test_4 ) FAILED

[+] RUNNING test_agg_1 :
    [+] A NEW INDEX ( test_agg_1 ) WAS CREATED
    [+] TIMESTAMP RANGE -- [2019-09-16T15:59:57 - 2019-09-16T15:59:57]
    [+] TESTING RULE -- AGG_RULE01 ( ./agg_rule01.yaml )
    [+] UPDATING RESULTS...
    [+] DELETING TEST INDEX...
    [+] TEST ( test_agg_1 ) FAILED

[+] RUNNING test_agg_02 :
    [+] TEST ( test_agg_2 ) WAS DISABLED


[+] RESULTS WERE OUTPUT TO CURRENT_WORKING_DIRECTORY/results.json

    ╒════════════╤══════════╤═════════════════════════════════════════════════════════════╕
    │ TestID     │ RESULT   │ MESSAGE                                                     │
    ╞════════════╪══════════╪═════════════════════════════════════════════════════════════╡
    │ test_1     │ PASSED   │                                                             │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_2     │ PASSED   │                                                             │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_3     │ FAILED   │ > 1 LOG(S) MATCHED: log001.json                             │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_4     │ FAILED   │ > 7 LOG(S) DID NOT MATCH: agg_log001.json, agg_log002.json, │
    │            │          │   agg_log003.json, agg_log004.json, agg_log005.json,        │
    │            │          │   log001.json, log003.json                                  │
    ├────────────┼──────────┼─────────────────────────────────────────────────────────────┤
    │ test_agg_1 │ FAILED   │ > HITS (5) EXCEEDED THE THRESHOLD                           │
    ╘════════════╧══════════╧═════════════════════════════════════════════════════════════╛
```
