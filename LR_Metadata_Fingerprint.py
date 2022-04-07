import csv
from collections import defaultdict
#import os

# WARNING WARNING WARNING WARNING
# This script might produce faulty output, make sure to validate against input before using. If there is an issue, it's probably in the main for loop

inputPath = r'C:\Users\EXAMPLE\Downloads\EXAMPLE-LogRhythm_WebLogsExport.csv'
outputPath = r'C:\Users\EXAMPLE\Desktop\EXAMPLE_Metadata_FIngerprint.csv'

#GROUP_BY_FIELD = 'Vendor Message ID'
GROUP_BY_FIELD = 'MPE Rule Name'
FIELDS_TO_IGNORE = ['Log Date','Log Sequence Number','First Log Date','Last Log Date','Log Message','Log Count','Log Source Entity','Zone (Origin)','Zone (Impacted)']
BAD_STRINGS = ['']

class logBucket:
	def __init__(self):
		self.fieldCounters = defaultdict(int)
		self.fieldUniqueValues = defaultdict(set)
		self.fieldPopulatedRates = defaultdict(float)
		self.fieldInformationContents = defaultdict(float)
		self.totalCount = 0
		# per field, what percent of the time is this populated?

	def printBucket(self):
		for k in self.fieldInformationContents.keys():
			print(f'Field: {k}, % Populated: {self.fieldPopulatedRates[k]}, Populated Count: {self.fieldCounters[k]}, Information Content: {self.fieldInformationContents[k]}, Unique Values: {len(self.fieldUniqueValues[k])}')
		print()

METADATA_DICT = defaultdict(logBucket)
TOTAL_LOGS = 0

def exportToCsv(path=outputPath):
	headers = [GROUP_BY_FIELD,'Field','% Populated','Populated Count','Information Content','Unique Values']
	with open(path, 'w', newline='') as outputFile:
		wr = csv.writer(outputFile, quoting=csv.QUOTE_ALL)
		wr.writerow(headers)
		for k,v in METADATA_DICT.items():
			for field in v.fieldInformationContents.keys():
				thisGroupByField = k
				thisField = field
				thisPercentPopulated = v.fieldPopulatedRates[field]
				thisPopulatedCount = v.fieldCounters[field]
				thisInformationContent = v.fieldInformationContents[field]
				thisUniqueValues = len(v.fieldUniqueValues[field])
				wr.writerow([thisGroupByField,thisField,thisPercentPopulated,thisPopulatedCount,thisInformationContent,thisUniqueValues])
	

with open(inputPath, 'r') as inputFile:
	csvReader = csv.DictReader(inputFile)
	for log in csvReader:
		TOTAL_LOGS += 1
		METADATA_DICT[log[GROUP_BY_FIELD]].totalCount += 1
		for field in log.keys():
			if (field not in FIELDS_TO_IGNORE) and (log[field] != ''):
				# increment counter for which this value is populated
				METADATA_DICT[log[GROUP_BY_FIELD]].fieldCounters[field] += 1
				# append unique values
				METADATA_DICT[log[GROUP_BY_FIELD]].fieldUniqueValues[field].add(log[field])
				# update populated rate (total values for field / total values for GROUP_BY_FIELD)
				METADATA_DICT[log[GROUP_BY_FIELD]].fieldPopulatedRates[field] = \
					METADATA_DICT[log[GROUP_BY_FIELD]].fieldCounters[field] / \
					METADATA_DICT[log[GROUP_BY_FIELD]].totalCount
				# update information content (unique values / total values for field)
				METADATA_DICT[log[GROUP_BY_FIELD]].fieldInformationContents[field] = \
					len(METADATA_DICT[log[GROUP_BY_FIELD]].fieldUniqueValues[field]) / \
					METADATA_DICT[log[GROUP_BY_FIELD]].fieldCounters[field]
		#if TOTAL_LOGS % 1000 == 0:
		#	#METADATA_DICT[GROUP_BY_FIELD].printBucket()
		#	for k,v in METADATA_DICT.items():
		#		print(f'Bucket: {k} (Hits: {METADATA_DICT[k].totalCount})')
		#		v.printBucket()
		#	print(f'Parsed {TOTAL_LOGS} logs')
		#	input('Press enter to continue')

exportToCsv()
