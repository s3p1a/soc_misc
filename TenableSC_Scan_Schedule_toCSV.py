#script will pull specific scan schedule details from a Tenable security center and format as csv
#uses https://github.com/tenable/pyTenable
#should be able to pip install pytenable
#docs: https://pytenable.readthedocs.io/en/latest/
#more info on queryable scan parameters at https://community.tenable.com/s/question/0D5f2000055NqewCAC/get-a-list-of-all-active-scans
import os
import time
from tenable.sc import TenableSC
import csv
import getpass

#uncomment these lines to override hardcoded IP and username
ip = input("Security Center IP: ")
username = input("Username: ")
password = getpass.getpass('Security Center password: ')

#comment these lines to override hardcoded IP and username
# !!! This is a security risk !!!
#ip = 'redacted'
#username = 'redacted'
#password = "redacted"

sc = TenableSC(ip)
sc.login(username, password)
scansDict = sc.scans.list(fields=['id','name','schedule','ipList'])
scansList = []

# pull list of scan results, then perform dictionary comprehension to convert
# list to dictionary indexed by scan name, which will be used for duration lookups
scanResultsDict = sc.scan_instances.list(fields=['id','name','scanDuration'])
manageableInstancesDict = {d["name"]: d for d in scanResultsDict['manageable']}

headers = 'Scan Name','IP List','Interval','By','Day Of Month','Day','Time', 'Duration'

for i in scansDict['manageable']:
	if (i['schedule']['repeatRule'] == ''):
		continue
	thisName = i['name']
	#iplist comes back as a string delimited by '\r', so replace with commas
	thisIPList = i['ipList'].replace('\r',', ')
	thisRepeatRule = i['schedule']['repeatRule'].split(';')
	thisInterval = thisRepeatRule[1].split("=")[1]
	thisBy = thisRepeatRule[2].split("=")[0]
	thisDayInt = ''.join(i for i in thisRepeatRule[2].split("=")[1] if i.isdigit())
	thisDayAlpha =  ''.join(i for i in thisRepeatRule[2].split("=")[1] if i.isalpha())
	thisTime = i['schedule']['start'].split(":")[1].split("T")[1]
	thisTime = thisTime[:2] + ':' + thisTime[2:4] + ':' + thisTime[4:]
	
	try:
		thisDuration = int(manageableInstancesDict[thisName]['scanDuration'])
	except KeyError:
		thisDuration = -1
	if (thisDuration != -1):
		thisDuration /= 60
	
	if thisBy == 'BYDAY':
		thisStr = thisName,thisIPList,thisInterval,thisBy,thisDayInt,thisDayAlpha,thisTime,thisDuration
	else:
		thisStr = thisName,thisIPList,thisInterval,thisBy,thisDayInt,'',thisTime,thisDuration
	
	scansList.append(thisStr)
	

filepath = os.path.expanduser(r'~\Desktop\Tenable_Scans_' +time.strftime("%Y%m%d-%H%M%S")+'.csv')
with open(filepath, 'w', newline='') as outputFile:
	wr = csv.writer(outputFile, quoting=csv.QUOTE_ALL)
	wr.writerow(headers)
	for i in scansList:
		wr.writerow(i)
		
print('CSV report written to ', filepath)
	
