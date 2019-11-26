from datetime import timedelta as dtd
from elasticsearch import Elasticsearch
from tabulate import tabulate
import argparse
import dateutil.parser as dp
import json
import os
import time
import yaml

# ===_PROGRAM_OPTIONS_==============================================

parser = argparse.ArgumentParser(
    prog='python ./elastalerter.py',
    usage="%(prog)s --logs LOGS_DIR --rules RULES_DIR --expected expected.json",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='''\
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
    }'''
)

parser.add_argument('--host', default="127.0.0.1", type=str, help='elasticsearch instance host address (default: %(default)s)')
parser.add_argument('--port', default=9200, type=int, help='elasticsearch instance port (default: %(default)d)')
parser.add_argument('--config', metavar="YAML", type=str, help='elastalert config file to use.')
parser.add_argument('--mappings', metavar="JSON", type=str, help='field data type mappings.')
parser.add_argument('--verbose', default=0, action="count", help='output other details')

arg_group = parser.add_argument_group('required arguments')
arg_group.add_argument('--expected', metavar="JSON", required=True, type=str, help='JSON outline of test names and expected results')
arg_group.add_argument('--logs', metavar="DIR", required=True, type=str, help='directory of the logs to be indexed')
arg_group.add_argument('--rules', metavar="DIR", required=True, type=str, help='directory of the rules to run with elastalert')

args = parser.parse_args()


# ===_CHECK_CONNECTION_TO_ELASTICSEARCH_============================

es = Elasticsearch([{'host':args.host, 'port':args.port}])
if not es.ping():
    print("\n[ERROR] CONNECTING TO ELASTICSEARCH FAILED\n")
    exit()


# ===_PRINT_MESSAGE_================================================

def printMessage(message, indention=4, info=None):
    if info == "fail": stdout = "\033[31m" + message + "\033[0m"
    elif info == "warn": stdout = "\033[33m" + message + "\033[0m"
    elif info == "pass": stdout = "\033[32m" + message + "\033[0m"
    elif info == "test": stdout = "\033[1;34m" + message + "\033[0m"
    else: stdout = message
    print(" "*indention + stdout)

    return message


# ===_CREATE_INDEX_=================================================

def createIndex(index):
    if args.mappings != None:
        with open(args.mappings) as mapping_file:
            mappings = json.load(mapping_file)
    else: mappings = None

    res = es.indices.create(index=index, ignore=400, body=mappings)
    if res.get("error", False): return False
    return True


# ===_DELETE_INDEX_=================================================

def deleteIndex(index):
    try:
        res = es.indices.delete(index=index)
        return True
    except: return False


# ===_FIND_LOGS_DIRECTORY_==========================================

def findLogsDirectory(test_logs):
    if type(test_logs) is str:
        if os.path.exists(test_logs): log_dir = test_logs
        elif os.path.exists(args.logs + "/" + test_logs): log_dir = args.logs + "/" + test_logs
        elif os.path.exists(os.getcwd() + "/" + test_logs): log_dir = os.getcwd() + "/" + test_logs
        else: 
            printMessage(f"[ERROR] DIRECTORY ( {test_logs} ) WAS NOT FOUND...", info="fail")
            return False
        printMessage(f"[+] SPECIFIED LOGS IS A DIRECTORY ( {log_dir.replace('//', '/')} )", info="warn")
    else: log_dir = args.logs
   
    return log_dir.replace("//", "/")

# ===_INDEX_LOGS_===================================================

def indexLogs(test_index, log_dir, log_list):
    log_refs = dict()
    start = ""
    end = ""
    messages = list()

    if not log_dir: return log_refs, start, end, messages

    invalid_files = list()
    for log_file in log_list:
        try:
            with open(log_dir + "/" + log_file) as log:
                try:
                    log_json = json.load(log)
                    id = log_json['_id']
                
                    try:
                        res = es.index(index=test_index, id=id, body=log_json['_source'])
                        log_refs.setdefault(test_index + "[-]" + id, log_file)
                        timestamp = log_json['_source']['real_timestamp']
                        if start == "" and end == "": start, end = timestamp, timestamp
                        else: start, end = updateLogRange( timestamp, start, end )
                    
                    except: messages.append( printMessage(f"[ERROR] {log_dir}/{log_file} WAS {res['result'].upper()}", 8, info="fail") )
                    
                except KeyError:
                    printMessage(f"[ERROR] \"{log_file}\" IS NOT A VALID LOG FILE.", 8, info="fail")
                    invalid_files.append(log_file)
                except json.decoder.JSONDecodeError:
                    printMessage(f"[ERROR] \"{log_file}\" IS NOT A VALID JSON FILE.", 8, info="fail")
                    invalid_files.append(log_file)
  
        except FileNotFoundError:
            messages.append( printMessage(f"[ERROR] \"{log_file}\" WAS NOT FOUND") )
            invalid_files.append(log_file)

    for i in invalid_files: log_list.remove(i)

    return log_refs, start, end, messages


# ===_UPDATE_LOG_TIMESTAMP_RANGE_===================================

def updateLogRange(timestamp, start, end):
    if dp.parse(timestamp) < dp.parse(start): start = timestamp
    elif dp.parse(timestamp) > dp.parse(end): end = timestamp

    return start, end


# ===_GENERATE_CONFIG_FILE_=========================================

def generateConfigFile(filename):
    with open("/tmp/config.yaml", "w") as config_file:
        config_file.write(f"rules_folder: {args.rules}\n")
        config_file.write("\nrun_every:\n    seconds: 30\n")
        config_file.write("\nbuffer_time:\n    minutes: 5\n")
        config_file.write(f"\nes_host: {args.host}\n\nes_port: {args.port}\n")
        config_file.write("\nwriteback_index: elastalert_status\nwriteback_alias: elastalert_alerts\n ")            
        config_file.write("\nalert_time_limit:\n    minutes: 1\n")

    return filename


# ===_UPDATE_RULE_FILE_=============================================

def updateRuleFile(rule_path, index, out_file):
    if os.path.exists(rule_path):
        if rule_path[-4:]==".yml" or rule_path[-5:]==".yaml":
            with open(rule_path) as rule_file:
                rule_yaml = yaml.safe_load(rule_file)
            
            rule_yaml["alert"] = "elastalerter.alerter.Alert"
            rule_yaml["index"] = index
            rule_yaml["doc_type"] = "_doc"

            if args.mappings == None and rule_yaml["type"] == "metric_aggregation":
                rule_yaml["query_key"] += ".keyword"
                rule_yaml["metric_agg_key"] += ".keyword"

            with open(out_file, "w") as test_rule:
                yaml.dump(rule_yaml, test_rule)

            return out_file, rule_yaml['name']

        else: printMessage(f"[ERROR] ( {rule_path} ) FILE EXTENTSION DOESN'T SEEM TO BE \".yaml\" OR \".yml\"", info="fail")
    else: printMessage(f"[ERROR] \"{rule_path}\" DOESN'T EXIST...", info="fail")

    return False, None


# ===_TEST_RULE_====================================================

def testRule(rule, start, end):
    try:
        start = (dp.parse(start[:-5]) - dtd(days=1)).isoformat()
        end = (dp.parse(end[:-5]) + dtd(days=0.5)).isoformat()

        os.system(f"elastalert-test-rule --alert --config {args.config} --start {start} --end {end} {rule} >/dev/null 2>&1")
        time.sleep(0.125)
                
        return True
                
    except ValueError: printMessage("[ERROR] THERE ARE NO INDEXED LOGS.", info="fail")
    
    return False


# ===_GENERATE_RESULTS_=============================================

def generateResults(test_id, test_param, indexed_logs): 
    test_results = {
        "result": "FAILED",
        "message": list()
    }

    alert_data = list()
    alert_file = "/tmp/alert_test_results.log"
    if not os.path.exists(alert_file): open(alert_file, 'w').close()
    with open(alert_file) as results_file:
        for result in results_file:
            alert_json = json.loads(result)
            alert_data.append(alert_json)
    os.system("rm /tmp/alert_test_results.log")

    if len(alert_data) == 0: 
        if test_param["match"] == False: test_results["result"] = "PASSED"
        else: test_results["message"].append("NO LOG(S) MATCHED.")
    
    else:
        matches = list()
        for i in alert_data:
            if i.get("index", False):
                match = i["index"] + "[-]" + i["id"]
                matches.append( indexed_logs[match] )
            else:
                if test_param["match"] == True: test_results["result"] = "PASSED"
                else: test_results["message"].append(f"HITS ({i['hits']}) EXCEEDED THE THRESHOLD")

                return test_results
        
        not_matches = [x for x in test_param["log"] if x not in matches]
        if not not_matches:
            if test_param["match"] == True: test_results["result"] = "PASSED"
            else: test_results["message"].append("SPECIFIED LOG(S) MATCHED.")
        else:
            if test_param["match"] == False:  test_results["message"].append(f"{len(matches)} LOG(S) MATCHED: " + ", ".join(matches))
            else:  test_results["message"].append(f"{len(not_matches)} LOG(S) DID NOT MATCH: " + ", ".join(not_matches))

    return test_results


# ===_TABULATE_RESULTS_=============================================

def tabulateResults(test_results):
    transformed_results = list()
    for i, test in enumerate(test_results['tests']):
        test_details = list()
        test_details.append(test)
        test_details.append(test_results['tests'][test].get('result', "N/A"))
        test_details.append(test_results['tests'][test].get('message'))

        for i in range(len(test_details[2])):
            message_text = ""
            line_length = 67
            while True:
                if len(test_details[2][i]) < line_length:
                    message_text += test_details[2][i]
                    break
                marker = test_details[2][i][:line_length].rfind(" ")
                message_text += test_details[2][i][:marker] + "\n  "
                test_details[2][i] = test_details[2][i][marker + 1:]
            test_details[2][i] = "> " + message_text

        if test_details[2] == []: test_details[2] = ""
        else: test_details[2] = "\n".join(test_details[2])
        transformed_results.append(test_details)

    table = tabulate(transformed_results, headers=["TestID", "RESULT", "MESSAGE"], tablefmt="fancy_grid")
    print("\n".join(" "*4 + x for x in table.splitlines()))


# ===_OUTPUT_TO_FILE_===============================================

def outputFile(filename, data):
    output_file = os.getcwd() + "/" + filename
    with open(output_file, 'w') as out_file:
        try: 
            out_file.write(data)
            return output_file
        except: return None


# ===_MAIN_FUNCTION_================================================

def main():
    if args.config != None:
        if not os.path.exists( args.config ): 
            printMessage("\n[ERROR] THE SPECIFIED CONFIG FILE WAS NOT FOUND.\n", 0, info="fail")
            exit()
    else: args.config = generateConfigFile("/tmp/config.yaml")

    if not os.path.exists( args.expected ):
        printMessage(f"\n[ERROR] ( {args.expected} ) WAS NOT FOUND", 0, info="fail")
        exit()

    with open( args.expected ) as expectations_file:
        expectations = json.load( expectations_file )

    tests = {
        "total": 0,
        "pass": int(),
        "fail": int(),
        "tests": dict()
    }

    for i, test in enumerate( expectations ):
        printMessage(f"\n[+] RUNNING {test} :", 0, info="test")

        if expectations[test]['enabled']:
            new_index = test.lower()
            
            if createIndex( new_index ):
                if args.verbose > 0: printMessage(f"[+] A NEW INDEX ( {new_index} ) WAS CREATED")
       
                log_dir = findLogsDirectory( expectations[test]["log"] )
                if type(expectations[test]["log"]) is str and log_dir: 
                    expectations[test]["log"] = sorted(os.listdir(log_dir))
                logs, start, end, messages = indexLogs( new_index, log_dir, expectations[test]['log'] )
                time.sleep(2)
            else: start, end = "", ""

            if start != "" and end != "": 
                if args.verbose > 0: printMessage(f"[+] TIMESTAMP RANGE -- [{start[:-5]} - {end[:-5]}]")
            
                rule = f"{args.rules}/{expectations[test]['rule']}".replace("//", "/")
                rule_file, rule_name = updateRuleFile( rule, new_index, "/tmp/rule.yaml" )
                if rule_file:
                    printMessage(f"[+] TESTING RULE -- {rule_name} ( {rule} )", info="warn")
                    testRule(rule_file, start, end)
            
                    if args.verbose > 0: printMessage("[+] UPDATING RESULTS...")
                    results = generateResults( test, expectations[test], logs )
                    
                    tests["total"] += 1
                    if results["result"] == "PASSED": tests["pass"] += 1
                    tests["tests"].setdefault(test, {
                        "result": results["result"], 
                        "message": messages + results["message"]
                    })
            
            if args.verbose > 0: printMessage("[+] DELETING TEST INDEX...")
            deleteIndex( new_index )
            time.sleep(0.15)

            if tests['tests'].get(test, False):
                if tests['tests'][test]['result'] == "PASSED": info = "pass"
                else: info = "fail"
                printMessage(f"[+] TEST ( {test} ) {tests['tests'][test]['result']}", info=info)
            else: printMessage(f"[+] TEST ( {test} ) ENCOUNTERED AN ERROR", info="warn")    
    
        else: printMessage(f"[+] TEST ( {test} ) WAS DISABLED", info="warn")

    tests["fail"] = tests["total"] - tests["pass"]
    out = outputFile( "results.json", json.dumps(tests, indent=4) )
    
    if out: printMessage(f"\n[+] RESULTS WERE OUTPUT TO {out}\n", 0, info="warn")

    tabulateResults( tests )


# ===_INITIALIZATION_===============================================

if __name__ == "__main__": main()


