from elastalert.alerts import Alerter, BasicMatchString
import json

class Alert(Alerter):

    required_options = set(['name'])

    def alert(self, matches):
        print(matches)
        for match in matches:
            with open("/tmp/alert_test_results.log", "a") as output_file:
                
                alert_data = { 'rule': self.rule["name"] }

                alert_data['index'] = match.get("_index")
                alert_data['id'] = match.get("_id")
                alert_data['hits'] = match.get("num_hits")
                alert_data['matches'] = match.get("num_matches")

                json.dump(alert_data, output_file)
                output_file.write("\n")

    def get_info(self):
        info = {
            'type': 'elastalert test alerter',
            'name': self.rule['name'],
            'output_file': '/tmp/alert_test_results.log'
        }
        
        return info
