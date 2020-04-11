# example https://github.com/rapid7/vm-console-client-python/blob/master/samples/list_assets.py
# install nexpose library with 'pip install git+https://github.com/rapid7/vm-console-client-python.git' (requires git client)
# install isodate with 'pip install isodate'

import rapid7vmconsole
import base64
import logging
import sys
import isodate
import csv
import os
import time
import getpass

# importing requests to suppress certificate warning
# ref: https://stackoverflow.com/questions/27981545/suppress-insecurerequestwarning-unverified-https-request-is-being-made-in-pytho
import requests
# make InsecureRequestWarning directly accessible
# if this wasn't directly accessible, following code could be collapsed to one line as
# requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#uncomment these lines to prompt for credentials
#username = input("Nexpose username: ")
#password = getpass.getpass("Nexpose password: ")

#uncomment these lines to use hardcoded credentials
username = 'redacted'
password = 'redacted'

nexpose_console = 'https://<example>:3780'

config = rapid7vmconsole.Configuration(name='Rapid7')
config.username = username
config.password = password
config.host = 'nexpose_console'
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

scans_api = rapid7vmconsole.ScanApi(client)
scan_pages = scans_api.get_scans(size=500).to_dict()['page']['total_pages']
page_counter = 0

scans_list = []
headers = 'Scan ID','Site Name','Duration','Start Time','Scan Engine'
scans_list.append(headers)

while (page_counter <= scan_pages):
		this_scan_list = (scans_api.get_scans(size=500,page=page_counter).to_dict()['resources'])
		print(f"Retrieved {len(this_scan_list)} items from page {page_counter}")
		page_counter += 1
		this_list = []
		for entry in this_scan_list:
			try:
				this_string = ''
				this_id = entry['id']
				this_site_name = entry['site_name']
				this_duration_minutes = int(isodate.parse_duration(entry['duration']).total_seconds()/60)
				this_start_time = entry['start_time']
				this_engine = entry['engine_name']
				this_string = this_id,this_site_name,this_duration_minutes,this_start_time,this_engine
				this_list.append(this_string)
			except:
				continue
		scans_list.extend(this_list)
		# print(this_list)

filepath = os.path.expanduser(r'~\Desktop\Nexpose_Scans_' +time.strftime("%Y%m%d-%H%M%S")+'.csv')
with open(filepath, 'w', newline='') as outputFile:
	wr = csv.writer(outputFile, quoting=csv.QUOTE_ALL)
	for i in scans_list:
		wr.writerow(i)		
print('CSV report written to ', filepath)
