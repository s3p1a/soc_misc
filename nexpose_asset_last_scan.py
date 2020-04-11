# install nexpose library with 'pip install git+https://github.com/rapid7/vm-console-client-python.git' (requires git client)
# install isodate with 'pip install isodate'
# sample code https://github.com/rapid7/vm-console-client-python/blob/master/docs/AssetApi.md#find_assets
# and https://github.com/rapid7/vm-console-client-python/blob/master/samples/list_assets.py

from __future__ import print_function
import time
import rapid7vmconsole
from rapid7vmconsole.rest import ApiException
from pprint import pprint
import logging
import sys
import base64
import csv
import os

# suppress insecure request warnings
import requests
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

username = ''
password = ''
nexpose_console = 'https://<example>:3780'

config = rapid7vmconsole.Configuration(name='Rapid7')
config.username = username
config.password = password
config.host = nexpose_console
config.verify_ssl = False
config.assert_hostname = False
config.proxy = None
config.ssl_ca_cert = None
config.connection_pool_maxsize = None
config.cert_file = None
config.key_file = None
config.safe_chars_for_path_param = ''

# Logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
logger.addHandler(ch)
config.debug = False


auth = "%s:%s" % (config.username, config.password)
auth = base64.b64encode(auth.encode('ascii')).decode()
client = rapid7vmconsole.ApiClient(configuration=config)
client.default_headers['Authorization'] = "Basic %s" % auth

def search_assets(field='host-name',operator='is',lower=None,upper=None,value='testhost',values=None):
	# create an instance of the API class
	api_instance = rapid7vmconsole.AssetApi(client)
	#param1 = rapid7vmconsole.SearchCriteria() # SearchCriteria | param1
	
	# this method works to use the library-provided class when defining filters
	# there may not be a reason to do this, but the example is included here because
	# using intermediate object and its included to_dict() method
	# (in rapid7vmconsole/models/swagger_search_criteria_filter.py) is how I derived proper
	# dict syntax
	# from rapid7vmconsole.models.swagger_search_criteria_filter import SwaggerSearchCriteriaFilter
	# filters = [SwaggerSearchCriteriaFilter(field="host-name",operator="is",value="testhost"),]
	
	# filters can also be defined by using a native dict:
	# note this dict must be embedded in an array, as the API expects an array
	filters = [{'field': field, 'lower': lower, 'operator': operator, 'upper': upper, 'value': value, 'values': values},]
	param1 = rapid7vmconsole.SearchCriteria(filters=filters,match='any')
	page = 0 # int | The index of the page (zero-based) to retrieve. (optional) (default to 0)
	size = 10 # int | The number of records per page to retrieve. (optional) (default to 10)
	#sort = ['sort_example'] # list[str] | The criteria to sort the records by, in the format: `property[,ASC|DESC]`. The default sort order is ascending. Multiple sort criteria can be specified using multiple sort query parameters. (optional)
	try:
		# Asset Search
		api_response = api_instance.find_assets(param1, page=page, size=size)
		# pprint(api_response)
		return api_response
	except ApiException as e:
		# print("Exception when calling AssetApi->find_assets: %s\n" % e)
		return None

def extract_IP_and_last_scan(api_response):
	try:
		ip = api_response.to_dict()['resources'][0]['addresses'][0]['ip']
		history = api_response.to_dict()['resources'][0]['history']
		history = sorted(history, key=lambda k: k['_date'],reverse=True)
		last_scan = history[0]['_date']
		return {'ip': ip, 'last_scan': last_scan}
	except Exception as e:
		# print('Caught exception while retrieving IP and Last Scan')
		return None

search_results = []
counter = 0
blockcounter = 0
misscounter = 0
print(f'[{time.strftime("%H:%M:%S")}] Starting {len(test_targets)} queries')
for target in test_targets:
	try:
		this_data = extract_IP_and_last_scan(search_assets(value=target))
		this_result = target,this_data['ip'],this_data['last_scan']
		search_results.append(this_result)
	except Exception as e:
		# print('miss')
		this_result = target,'No Data','No Data'
		search_results.append(this_result)
		misscounter += 1
	except KeyboardInterrupt:
		break
	counter += 1
	blockcounter += 1
	# print(f'counter: {counter}, blockcounter: {blockcounter}')
	if blockcounter == 50:
		print(f'[{time.strftime("%H:%M:%S")}] processed {counter} of {len(test_targets)} queries with {misscounter} misses')
		blockcounter = 0
		
filepath = os.path.expanduser(r'~\Desktop\Nexpose_Assets_' +time.strftime("%Y%m%d-%H%M%S")+'.csv')
with open(filepath, 'w', newline='') as outputFile:
	wr = csv.writer(outputFile, quoting=csv.QUOTE_ALL)
	for i in search_results:
		wr.writerow(i)		
print('CSV report written to ', filepath)