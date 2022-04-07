import csv
from collections import defaultdict

inputPath = r'C:\Users\3355505\Downloads\07_12_2021-LogRhythm_WebLogsExport(logMessage).csv'
outputPath = r'C:\Users\3355505\Desktop\s1_metadata_fingerprints.csv'

def getMetadataFingerprint(inputString):
	stringFields = inputString.split('|')
	thisActivityType = 'NA'
	for field in stringFields:
		thisMetadata = field.split('=')[0]
		if thisMetadata == 'activityType':
			thisActivityType = field.split('=')[1].replace('"','').strip()
	metadataFields = [field.split('=')[0] for field in stringFields][4:]
	metadataFingerprint = '' + thisActivityType + ','
	for field in metadataFields:
		if ' ' in field:
			continue
		else:
			metadataFingerprint += field
			metadataFingerprint += '|'
	metadataFingerprint = metadataFingerprint.strip('|')
	return(metadataFingerprint)
	

fingerprintSet = set()
fingerprintDict = defaultdict(set)
with open(inputPath, 'r', encoding='utf8'	) as inputFile:
	next(inputFile)
	for line in inputFile:
		try:
			thisLineFingerprint = getMetadataFingerprint(line)
			thisFingerprint = thisLineFingerprint.split(',')[1]
			thisActivityType = thisLineFingerprint.split(',')[0]
			fingerprintDict[thisFingerprint].add(thisActivityType)
		except UnicodeDecodeError:
			continue
		
with open (outputPath, 'w') as outputFile:
	for k,v in fingerprintDict.items():
		thisString = ''
		for activityType in v:
			thisString += activityType
			thisString += '|'
		thisString = thisString.strip('|')
		outputFile.writelines(f'{thisString},{k}\n')