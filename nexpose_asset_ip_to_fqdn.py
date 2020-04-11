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
import getpass
import argparse

# suppress insecure request warnings
import requests
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

username = ''
password = ''
nexpose_console = 'https://<example>:3780'

#username = input("Username: ")
#password = getpass.getpass('Security Center password: ')

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
		
def fqdn_from_ip(ip):
	api_response = search_assets(field='ip-address',operator='is',lower=None,upper=None,value=ip,values=None)
	try:
		fqdn = api_response.to_dict()['resources'][0]['host_name']
	except IndexError:
		fqdn = 'Not found'
	return {'ip': ip, 'fqdn': fqdn}
	
parser = argparse.ArgumentParser("Lookup a hostname in Nexpose's database by IP")
parser.add_argument('-s','--single', help='Specify a single IP to lookup')
parser.add_argument('-f','--file', help='Specify a list of IPs to lookup from a file, one per line')
args = parser.parse_args()

if (args.single and args.file) or (not args.single and not args.file):
	print('Please specify either a single IP address or a file')
	parser.print_help()
	raise SystemExit

if args.single:
	response = fqdn_from_ip(args.single)
	print(f"{response['ip']},{response['fqdn']}")

if args.file:
	with open(args.file, 'r') as inputfile:
		for line in inputfile:
			response = fqdn_from_ip(line.rstrip())
			print(f"{response['ip']},{response['fqdn']}")
