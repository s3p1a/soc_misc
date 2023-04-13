import csv
import os
import datetime
import re
import pathlib
from collections import defaultdict

fullInputPath = r'C:\Users\<redact>\Downloads\WebLogsExport(logMessage).csv'

sampleInputLog = r'06 05 2021 23:30:48 10.35.21.68 <SAU1:INFO> Jun 05 23:30:48 hostname.redact.com W3CLogs_logrhythm: Info: 1622957447.316 90297 10.48.28.132 - 51072 40.97.137.146 443 tunnel://outlook.office365.com:443/ 4621 6219 6180 - - CONNECT 200 - - TCP_MISS - - - - <IW_pem,9.2,1,"-",-,-,-,-,"-",-,-,-,"-",-,-,"-","-",-,-,IW_pem,-,"-","Organizational Email","-","Office 365/OneDrive","Office Suites","Encrypted","-",0.55,0,-,"-","-",-,"-",-,-,"-","-",-,-,"-",->'
sampleInputScanResult = sampleInputLog.split('<')[2].strip('>').split(',')

valuesDict = defaultdict(lambda: set())

# enable unique values logging for a given column, True = Enabled
fieldsToggle = {
	1 : False,
	2 : False,
	3 : True,
	4 : False,
	5 : True,
	6 : True,
	7 : True,
	8 : True,
	9 : True,
	10 : True,
	11 : True,
	12 : True,
	13 : True,
	14 : True,
	15 : True,
	16 : False,
	17 : False,
	18 : True,
	19 : True,
	20 : True,
	21 : True,
	22 : True,
	23 : False,
	24 : True,
	25 : False,
	26 : False,
	27 : False,
	28 : True,
	29 : False,
	30 : True,
	31 : True,
	32 : True,
	33 : True,
	34 : True,
	35 : True,
	36 : True,
	37 : True,
	38 : True,
	39 : True,
	40 : True,
	41 : True,
	42 : True,
	43 : True,
}

'''
baseOutputPath = pathlib.Path.home()/'Desktop'
#fullOutputPath = os.path.join(basePath,rf"WSA_Log_Parsing_Sample_{datetime.date.today()}.csv")
fullOutputPath = os.path.join(baseOutputPath,rf"WSA_Log_Parsing_Sample.csv")
with open(fullOutputPath, 'w', newline='') as outputFile:
	wr = csv.writer(outputFile, HEADERS)
	wr.writerow(HEADERS)
	with open(fullInputPath,'r') as inputFile:
		for line in inputFile:
			try:
				wr.writerow(line.split('<')[2].strip('>').split(','))
			except IndexError:
				print(line)
print('CSV report written to ', rf'{fullOutputPath}')
'''
with open(fullInputPath,'r') as inputFile:
	for line in inputFile:
		try:
			scanResult = line.split('<')[2].strip('>').split(',')
			#check cases where category fields 1 and 20 do not match
			if (scanResult[0] != scanResult[19]):
				#print(f'{scanResult[0]} != {scanResult[19]}')
				#print(line)
				pass
			# use enumerate to reference specific indices in the scanResult array and index against fieldsToggle
			for value in enumerate(scanResult):
				print(value)
				#check for specific category values in field 20
				#if value[0]+1 == 20 and (value[1] == 'IW_cryp'):
					#print(line)
				# check for non-null values in field 22
				#if value[0]+1 == 22 and (value[1] != '""-""') and (value[1] != '""Unknown""'):
					#print(value[1])
					#print(line)
				if fieldsToggle[value[0]+1] and (value[1] != '""-""'):
					valuesDict[value[0]+1].add(value[1])
		except IndexError:
			#print(line)
			pass

print(valuesDict)
