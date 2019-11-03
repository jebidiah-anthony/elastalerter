from datetime import timedelta as dtd
from elasticsearch import Elasticsearch
from tabulate import tabulate
import argparse
import dateutil.parser as dp
import json
import os
import time
import yaml

parser = argparse.ArgumentParser(
    prog='./test.py',
    usage="%(prog)s --logs LOGS_DIR --rules RULES_DIR --expected expected.json",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='''\
    SAMPLE "expected.json"
    ------------------------------------------------
    {
        "test_id": {
            "rule": "rule.yaml",
            "log": ["log1.json", "log2.json", ...],
            "match": (True | False)
        },
        "test_id": {
            ...
        }
    }'''
)

parser.add_argument('--host', default="127.0.0.1", type=str, help='elasticsearch instance host address (default: %(default)s)')
parser.add_argument('--port', default=9200, type=int, help='elasticsearch instance port (default: %(default)d)')
parser.add_argument('--config', metavar="YAML", type=str, help='elastalert config file to use.')
parser.add_argument('--verbose', action="count", help='output other details')

arg_group = parser.add_argument_group('required arguments')
arg_group.add_argument('--expected', metavar="JSON", required=True, type=str, help='JSON outline of test names and expected results')
arg_group.add_argument('--logs', metavar="DIR", required=True, type=str, help='directory of the logs to be indexed')
arg_group.add_argument('--rules', metavar="DIR", required=True, type=str, help='directory of the rules to run with elastalert')

args = parser.parse_args()

es = Elasticsearch([{'host':args.host, 'port':args.port}])
if not es.ping():
    print("\n    [ERROR] CONNECTING TO ELASTICSEARCH FAILED\n")
    exit()

def indexLogs(log_list):
    log_refs = dict()
    start = ""
    end = ""   

    for log_file in log_list:
        try:
            with open(args.logs + "/" + log_file) as log:
                try:
                    log_json = json.load(log)
                    index = log_json['_index']
                    id = log_json['_id']
                
                    try:
                        res = es.index(index=index, id=id, doc_type=log_json['_type'], body=log_json['_source'])
                        log_refs.setdefault(index + "[-]" + id, log_file)
                    
                        timestamp = log_json['_source']['real_timestamp']
                        if start == "" and end == "": start, end = timestamp, timestamp
                        else: start, end = updateLogRange( timestamp, start, end )
                    
                    except:
                        print("    [ERROR]" + args.logs + "/" + log_file + " WAS NOT INDEXED")
                    
                except KeyError:
                    print("    [ERROR] \"{}\" IS NOT A VALID LOG FILE".format(log_file))
                except json.decoder.JSONDecodeError:
                    print("    [ERROR] \"{}\" IS NOT A VALID JSON FILE".format(log_file))

        except FileNotFoundError:
            print("    [ERROR] \"{}\" WAS NOT FOUND".format(log_file))

    return log_refs, start, end

def deleteLogs(log_list):
    for i in log_list:
        curr = i.split("[-]")
        try: res = es.delete(index=curr[0], id=curr[1])
        except: print("    " + curr[0] + "-" + curr[1] + " | was not deleted")

def updateLogRange(timestamp, start, end):
    if dp.parse(timestamp) < dp.parse(start):
        start = timestamp
    elif dp.parse(timestamp) > dp.parse(end):
        end = timestamp

    return start, end

def generateConfigFile(filename):
    with open("/tmp/config.yaml", "w") as config_file:
        config_file.write(f"rules_folder: {args.rules}\n")
        config_file.write("\nrun_every:\n    seconds: 30\n")
        config_file.write("\nbuffer_time:\n    minutes: 5\n")
        config_file.write(f"\nes_host: {args.host}\n\nes_port: {args.port}\n")
        config_file.write("\nwriteback_index: elastalert_status\nwriteback_alias: elastalert_alerts\n ")            
        config_file.write("\nalert_time_limit:\n    minutes: 1\n")

    return filename

def testRule(rule, start, end):
    if os.path.exists(rule):
        if rule[-4:]==".yml" or rule[-5:]==".yaml":
            with open(rule) as rule_file:
                rule_yaml = yaml.safe_load(rule_file)
                rule_yaml["alert"] = "elastalerter.alerter.Alert"

            with open("/tmp/rule.yaml", "w") as test_rule:
                yaml.dump(rule_yaml, test_rule)

            try:
                start = (dp.parse(start[:-5]) - dtd(days=0.25)).isoformat()
                end = (dp.parse(end[:-5]) + dtd(days=0.25)).isoformat()

                print("    [+] TESTING RULE ( {} )".format(rule))
                time.sleep(0.15)
                os.system(f"elastalert-test-rule --alert --config {args.config} --start {start} --end {end} /tmp/rule.yaml >/dev/null 2>&1")
                
                return True
                
            except ValueError: print("    [ERROR] THERE ARE NO INDEXED LOGS.")
        else: print(f"    [ERROR] ({rule}) FILE EXTENTSION DOESN'T SEEM TO BE \".yaml\" OR \".yml\"")
    else: print(f"    [ERROR] ({rule}) FILE DOESN'T EXIST...")
    
    return False

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
            if test_param["match"] == False:  test_results["message"].append("MATCHED: " + ", ".join(matches))
            else:  test_results["message"].append("DID NOT MATCH: " + ", ".join(not_matches))

    return test_results

def tabulateResults(test_results):
    transformed_results = list()
    for i, test in enumerate(test_results['tests']):
        test_details = list()
        test_details.append(test)
        test_details.append(test_results['tests'][test].get('result', "N/A"))
        test_details.append(test_results['tests'][test].get('message'))
        
        for i in range(len(test_details[2])):
            message_text = ""
            line_length = 69
            while True:
                if len(test_details[2][i]) < line_length:
                    message_text += test_details[2][i]
                    break
                marker = test_details[2][i][:line_length].rfind(" ")
                message_text += test_details[2][i][:marker] + "\n  "
                message = test_details[2][i][marker + 1:]
            test_details[2][i] = "> " + message_text

        if test_details[2] == []: test_details[2] = ""
        else: test_details[2] = "\n".join(test_details[2])
        transformed_results.append(test_details)

    table = tabulate(transformed_results, headers=["TestID", "RESULT", "MESSAGE"], tablefmt="fancy_grid")
    print("\n".join("    " + x for x in table.splitlines()))

def outputFile(filename, data):
    output_file = os.getcwd() + "/" + filename
    with open(output_file, 'w') as out_file:
        try: 
            out_file.write(data)
            return output_file
        except: pass

    return None

def main():
    if args.config != None:
        if not os.path.exists(arg_file): exit()
    else:
        args.config = generateConfigFile("/tmp/config.yaml")

    with open( args.expected ) as expectations_file:
        expectations = json.load( expectations_file )

    tests = {
        "total": 0,
        "pass": int(),
        "fail": int(),
        "tests": dict()
    }

    for i, test in enumerate( expectations ):
        print(f"\n[+] RUNNING {test}\n")

        if args.verbose != None: print("    [+] INDEXING SPECIFIED LOGS...")
        logs, start, end = indexLogs( expectations[test]['log'] )
        if args.verbose != None: print(f"    [+] TIMESTAMP RANGE -- [{start[:-5]} - {end[:-5]}]")
        
        rule = f"{args.rules}/{expectations[test]['rule']}"
        if testRule(rule, start, end):
            if args.verbose != None: print(f"    [+] UPDATING RESULTS...")
            results = generateResults( test, expectations[test], logs )
            tests["tests"].setdefault(test, {"result": results["result"], "message": results["message"]})
            
        if args.verbose != None: print(f"    [+] CLEARING INDEXED LOGS...")
        deleteLogs( list(logs) )

        if args.verbose != None: print(f"    [+] TEST ( {test} ) DONE")

    out = outputFile( "results.json", json.dumps(tests, indent=4) )
    
    if out: print(f"\n[+] RESULTS WERE OUTPUT TO {out}\n")

    tabulateResults( tests )

    print("\n")

if __name__ == "__main__": main()