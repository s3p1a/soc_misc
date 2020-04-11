# this script will take an input CSV file of assets as (repository, ip address),
# look them up in a Tenable SC console, and return 
# a csv of ip address, dns name, netbios hostname, and OS version

import os
import time
from tenable.sc import TenableSC
import csv
import getpass

#sc.repositories.list() can return ID for a given repo name

#uncomment these lines to override hardcoded IP and username
ip = input("Security Center IP: ")
username = input("Username: ")
password = getpass.getpass('Security Center password: ')
input_csv = r'/path/to/csv'

sc = TenableSC(ip)
sc.login(username, password)

errorList = []
deviceList = []
headers = 'IP','DNS','NetBIOS','OS'
deviceList.append(headers)
errorList.append(headers)
with open(input_csv, mode='r') as csv_file:
	csv_reader = csv.DictReader(csv_file)
	
	rowcount = 0
	for row in csv_reader:
		thisCounter = 0
		while True:
			try:
				this_device = sc.repositories.device_info(int(row['Repository']), ip=row['IP Address'])
				this_os = this_device['os']
				this_os = this_os.replace("<br/>", " ")
				if (len(this_os) > 0):
					if (this_os[0] == ' '):
						this_os = this_os[1:]
				print(this_os)
				this_ip = this_device['ip']
				this_dns = this_device['dnsName']
				this_netbios = this_device['netbiosName']
				this_string = this_ip,this_dns,this_netbios,this_os
				rowcount += 1
				print('processed ', rowcount, ' rows')
#				if (rowcount > 9):
#					break
			except KeyboardInterrupt:
				quit()
			except:
				thisCounter += 1
				print('Read bad data for IP ', row['IP Address'], ', attempt ', thisCounter)
				if thisCounter > 2:
					this_ip = this_device['ip']
					this_dns = 'error'
					this_netbios = 'error'
					this_os = 'error'
					this_string = this_ip,this_dns,this_netbios,this_os
					print('Max error attempts reached on record, adding to error list')
					print(this_device)
					print(this_string)
					errorList.append(this_string)
					deviceList.append(this_string)
		#			input('Enter to quit')
					break
				else:
					continue
			else:
				deviceList.append(this_string)
				break

filepath = os.path.expanduser(r'~\Desktop\Tenable_Devices_' +time.strftime("%Y%m%d-%H%M%S")+'.csv')
with open(filepath, 'w', newline='') as outputFile:
	wr = csv.writer(outputFile, quoting=csv.QUOTE_ALL)
	for i in deviceList:
		wr.writerow(i)
		
print('CSV report written to ', filepath)