import csv
from collections import defaultdict

inputPath = r'C:\users\EXAMPLE\downloads\EXAMPLE.csv'
outputPath = r'C:\users\3355505\desktop\PA_Anomalous_Users.csv'

USER_DICT = defaultdict(lambda: defaultdict(set))


def parseFileToGlobalDict(inputPath):
	with open(inputPath,'r') as inputFile:
		inputDict = csv.DictReader(inputFile)
		for log in inputDict:
			thisUser = log['Source User']
			thisRegion = log['srcregion']
			thisMachineName = log['machinename']
			thisIP = log['public_ip']
			
			#thisUser = log['User']
			#thisRegion = log['Source Region']
			#thisMachineName = log['Computer']
			#thisIP = log['Public IP']
			
			#print(thisUser,thisRegion,thisMachineName,thisIP)
			
			USER_DICT[thisUser]['regions'].add(thisRegion)
			USER_DICT[thisUser]['machines'].add(thisMachineName)
			USER_DICT[thisUser]['ips'].add(thisIP)
			
			USER_DICT[thisUser]['userName'] = thisUser
			USER_DICT[thisUser]['regionCount'] = len(USER_DICT[thisUser]['regions'])
			USER_DICT[thisUser]['machineCount'] = len(USER_DICT[thisUser]['machines'])
			USER_DICT[thisUser]['ipCount'] = len(USER_DICT[thisUser]['ips'])
			USER_DICT[thisUser]['anomalyCount'] = USER_DICT[thisUser]['regionCount'] + USER_DICT[thisUser]['machineCount'] + USER_DICT[thisUser]['ipCount']
			

parseFileToGlobalDict(inputPath)

# return only anmalous users
ANOMALOUS_DICT = {k:v for k,v in USER_DICT.items() if (v['regionCount'] > 0 or v['machineCount'] > 0 or v['ipCount'] > 0)}
print(ANOMALOUS_DICT)

with open(outputPath, 'w',newline='') as outputFile:
	headers = ['User','RegionCount','MachineCount','IPCount','AnomalyCount','Regions','Machines','IPs']
	wr = csv.writer(outputFile, quoting=csv.QUOTE_ALL)
	wr.writerow(headers)
	for user in ANOMALOUS_DICT.values():
		wr.writerow([
			user['userName'],
			user['regionCount'],
			user['machineCount'],
			user['ipCount'],
			user['anomalyCount'],
			user['regions'],
			user['machines'],
			user['ips']
		])