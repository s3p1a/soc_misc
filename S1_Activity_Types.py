import re
import string

inputPath = r'C:\Users\3355505\Downloads\09_09_2021-LogRhythm_WebLogsExport(logMessage).csv'
#inputPath = r'C:\Users\3355505\Downloads\07_12_2021-LogRhythm_WebLogsExport(logMessage).csv'
outputPath = r'C:\Users\3355505\Desktop\s1_metadata_fingerprints_9-9-21.csv'

# general purpose method to parse a single S1 log into a dict - reuse this
COMMAND_LINE_PATTERN = re.compile('threatCommandLineArguments=.*\|threatID=')
def parseS1LogToDict(inputLog):
	thisDict = {}
	# strip out non printable characters
	inputLog = ''.join(filter(lambda x: x in string.printable, inputLog))
	# correct for cases where threat command line arguments contain pipes by pulling them out and parsing separately		
	if 'threatCommandLineArguments' in inputLog:
		# extract the command line
		thisCommandLine = re.search(COMMAND_LINE_PATTERN,inputLog).group(0)
		# strip preceding 'threatCommandLineArguments='
		thisCommandLine = re.sub('threatCommandLineArguments=','',thisCommandLine)
		# strip tailing '|threatID'
		thisCommandLine = re.sub('\|threatID=','',thisCommandLine)
		thisDict['threatCommandLineArguments'] = thisCommandLine
		thisLog = re.sub(COMMAND_LINE_PATTERN,'threatID=',inputLog)
	else:
		thisLog = inputLog
	thisMetadataFields = thisLog.split('|')
	thisDict['os'] = thisMetadataFields[3]
	for field in thisMetadataFields[4:]:
		try:
			thisDict[field.split('=')[0]] = field.split('=')[1]
		except Exception as e:
			print(f'Error [{e}] encountered while assigning a field value in the following log. This field will be ignored.')
			print(f'Field: {field}')
			print(inputLog)
			#input('Press enter to continue')
	thisDict['activityType'] = thisDict['activityType'].strip()
	thisDict['activityType'] = thisDict['activityType'].strip('"')
	return(thisDict)

Activity_Types_Dict = {}
with open(inputPath, 'r',encoding='utf8') as inputFile:
	next(inputFile)
	for line in inputFile:
		thisLog = parseS1LogToDict(line)
		thisActivityType = thisLog['activityType']
		thisEventDesc = thisLog['eventDesc'].split(' -')[0]
		Activity_Types_Dict[thisActivityType] = thisEventDesc

for activityType,eventDesc in Activity_Types_Dict.items():
	print(f'{activityType},{eventDesc}')
