#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import sys
import json
from thehive4py.api import TheHiveApi
from thehive4py.query import *
import datetime
import csv
import os

THE_HIVE_URL = 'http://127.0.0.1:9000'
THE_HIVE_API_KEY = 'yourKeyHere'

# pre-populate a dictionary of user names, as only the user ID is present in case
# json. '_TheHiveApi__find_rows' is a way to access the __find_rows private method
# within the TheHiveApi class.
# See https://stackoverflow.com/questions/9145499/calling-private-function-within-the-same-class-python
# and https://www.geeksforgeeks.org/name-mangling-in-python/ for additional details
USER_DICT = {item['id']:item['name'] for item in api._TheHiveApi__find_rows('/api/user/_search').json()}

# define fields to be extracted from json response, as well as any post-processing
# desired for output formatting, all of which occur in by customParseJson()
CASE_FIELDS_TO_PARSE = [
	{
		'jsonField':'serviceNowTicketNumber',
		'displayName':'SNOW Ticket #(s)',
		'isCustom':True,
		'postProcessing':None,
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	},
	{
		'jsonField':'title',
		'displayName':'Internal Incident #(s)',
		'isCustom':False,
		'postProcessing':lambda x:x.split('] ')[1],
		'functionOnPostProcessingException':lambda x:x.split(' ')[0],
		'valueOnPostProcessingException':None,
	},
	{
		'jsonField':'severity',
		'displayName':'Level',
		'isCustom':False,
		'postProcessing':None,
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	},
	{
		'jsonField':'classification',
		'displayName':'Classification',
		'isCustom':True,
		'postProcessing':None,
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	},
	{
		'jsonField':'status',
		'displayName':'Status',
		'isCustom':False,
		'postProcessing':None,
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	},
	{
		'jsonField':'startDate',
		'displayName':'Opened',
		'isCustom':False,
		'postProcessing':lambda x:datetime.date.fromtimestamp(x/1000).strftime('%m/%d/%Y'),
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	},
	{
		'jsonField':'createdBy',
		'displayName':'Handler',
		'isCustom':False,
		# post processing to convert user ID to 
		'postProcessing':lambda x:USER_DICT[x].split(' ')[1],
		'functionOnPostProcessingException':lambda x:USER_DICT[x].split(' ')[0],
		'valueOnPostProcessingException':None,
	},
	{
		'jsonField':'intakeSystem',
		'displayName':'Intake System',
		'isCustom':True,
		'postProcessing':None,
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	},
	{
		'jsonField':'reimage',
		'displayName':'Reimage',
		'isCustom':True,
		'postProcessing':None,
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	},
	{
		'jsonField':'user',
		'displayName':'User(s)',
		'isCustom':True,
		'postProcessing':lambda x:x.replace('\\\\','\\'),
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	},
		{
		'jsonField':'system',
		'displayName':'Systems',
		'isCustom':True,
		'postProcessing':lambda x:x.encode().decode('unicode_escape'),
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	}
]

api = TheHiveApi(THE_HIVE_URL, THE_HIVE_API_KEY)

# search query syntax https://github.com/TheHive-Project/TheHive4py/blob/master/thehive4py/query.py
# from examples at https://github.com/TheHive-Project/TheHive4py/blob/master/samples/test-case-search.py
def search(title, query, range, sort):
	#print(title)
	#print('-----------------------------')
	response = api.find_cases(query=query, range=range, sort=sort)

	if response.status_code == 200:
		jsonResponse = response.json()
		#print(json.dumps(jsonResponse, indent=4, sort_keys=True))
		#print('')
	else:
		print('ko: {}/{}'.format(response.status_code, response.text))
		sys.exit(0)
	return jsonResponse

def customParseJson(thisJson, fields=CASE_FIELDS_TO_PARSE):
	headers = []
	for field in CASE_FIELDS_TO_PARSE:
		headers.append(field['displayName'])
	listOfLists = []
	#print(json.dumps(thisJson, indent=4, sort_keys=True))
	for item in thisJson:
		thisList = []
		for field in CASE_FIELDS_TO_PARSE:
			if field['isCustom']:
				try:
					thisField = item['customFields'][field['jsonField']]['string']
					# handle cases where key exists but value is null
					if thisField is None:
						thisField = ''
						thisList.append(thisField)
						continue
				except (KeyError,AttributeError):
					#print(f'[!] Error: Field Not Found')
					thisField = ''
					thisList.append(thisField)
					continue
			else:
				try:
					thisField = item[field['jsonField']]
				except (KeyError,AttributeError):
					print(f"[!] Error: Field {field['jsonField']} Not Found")
					thisField = ''
					continue
			if field['postProcessing']:
				try:
					thisField = field['postProcessing'](thisField)
				except:
					if field['functionOnPostProcessingException']:
						thisField = field['functionOnPostProcessingException'](thisField)
						try:
							thisField = field['functionOnPostProcessingException'](thisField)
						except:
							if field['valueOnPostProcessingException']:
								thisField = thisField = field['valueOnPostProcessingException']
							else:
								print("[!] Error: Unhandled postprocessing exception")
								print(json.dumps(item, indent=4, sort_keys=True))
								print(field)
								System.exit(0)
					elif field['valueOnPostProcessingException']:
						thisField = field['valueOnPostProcessingException']
					else:
						print("[!] Error: Unhandled postprocessing exception")
						print(json.dumps(item, indent=4, sort_keys=True))
						print(field)
						System.exit(0)
			thisList.append(thisField)
		listOfLists.append(thisList)
	# this sort will only work when sorting by opened time, and it is in column 5
	# print(listOfLists)
	listOfLists.sort(key = lambda x:datetime.datetime.strptime(x[5],'%m/%d/%Y'),reverse=True)
	return {'headers':headers,'caseList':listOfLists}

def getStartOfWeeklyReportingPeriod(date):
	dayOfWeek = date.weekday()
	if dayOfWeek < 4:
		startDelta = dayOfWeek + 3
	elif dayOfWeek == 4:
		if date.hour < 17:
			startDelta = 7
		else:
			startDelta = 0
	else:
		startDelta = dayOfWeek - 4
	startOfWeeklyReportingPeriod = (date - datetime.timedelta(days=startDelta)).replace(hour=17,minute=0,second=0,microsecond=0)
	return startOfWeeklyReportingPeriod

def getEndOfWeeklyReportingPeriod(date):
	dayOfWeek = date.weekday()
	if dayOfWeek < 4:
		endDelta = 4 - dayOfWeek
	elif dayOfWeek == 4:
		if date.hour < 17:
			endDelta = 0
		else:
			endDelta = 7
	else:
		endDelta = 11 - dayOfWeek
	endOfWeeklyReportingPeriod = (date + datetime.timedelta(days=endDelta)).replace(hour=17,minute=0,second=0,microsecond=0)
	return endOfWeeklyReportingPeriod

def getStartOfMonth(date):
	return date.replace(day=1,hour=0,minute=0,second=0,microsecond=0)

def getEndOfMonth(date):
	# https://stackoverflow.com/questions/42950/how-to-get-the-last-day-of-the-month
	next_month = date.replace(day=28) + datetime.timedelta(days=4)
	endOfMonth = (next_month - datetime.timedelta(days=next_month.day)).replace(hour=23,minute=59,second=59,microsecond=999999)
	return endOfMonth

def datetimeToHiveTimestamp(datetime):
	return int(datetime.timestamp()) * 1000

def getCasesByTimeWindow(startDatetime,endDatetime):
	# search function expects epoch timestamp with milliseconds, so convert
	startTimestamp = datetimeToHiveTimestamp(startDatetime)
	endTimestamp = datetimeToHiveTimestamp(endDatetime)
	# search function expects a title, so may as well populate it here
	titleString=f'TheHive Cases, {startDatetime.strftime("%m-%d-%Y")} to {endDatetime.strftime("%m-%d-%Y")}'
	cases = customParseJson(search(titleString,Between('startDate',startTimestamp, endTimestamp), 'all', []))
	return {'startDatetime':startDatetime,'endDatetime':endDatetime,'caseList':cases['caseList'],'headers':cases['headers']}
	
def exportCaseDictToCSV(caseDict,basePath=os.path.expanduser(r'~\Desktop')):
	# join basePath to CSV filename format
	# check if report is time-bound, and append start/end if so
	if 'startDateTime' in caseDict.keys():
		fullPath = os.path.join(basePath,rf"TheHive_Cases_{caseDict['startDatetime'].strftime('%m-%d-%Y')}_to_{caseDict['endDatetime'].strftime('%m-%d-%Y')}.csv")
	# if not time-bound, add 'ALL_TIME' to filename instead of start/end
	else:
		fullPath = os.path.join(basePath,rf"TheHive_Cases_All_Time.csv")
	# append headers supplied in caseDict
	headers = caseDict['headers']
	with open(fullPath, 'w', newline='') as outputFile:
		wr = csv.writer(outputFile, quoting=csv.QUOTE_ALL)
		wr.writerow(headers)
		for case in caseDict['caseList']:
			wr.writerow(case)
	print('CSV report written to ', rf'{fullPath}')

def getCasesWeeklyReportingPeriod(date):
	start = getStartOfWeeklyReportingPeriod(date)
	end = getEndOfWeeklyReportingPeriod(date)
	cases = getCasesByTimeWindow(start,end)
	return cases

def getCasesForMonth(date):
	start = getStartOfMonth(date)
	end = getEndOfMonth(date)
	cases = getCasesByTimeWindow(start,end)
	return cases

def exportCasesCurrentWeeklyReportingPeriod():
	cases = getCasesWeeklyReportingPeriod(datetime.datetime.now())
	exportCaseDictToCSV(cases)
	
def exportCasesPreviousWeeklyReportingPeriod():
	cases = getCasesWeeklyReportingPeriod(datetime.datetime.now() - datetime.timedelta(days=7))
	exportCaseDictToCSV(cases)

def exportCasesMonthToDate():
	cases = getCasesForMonth(datetime.datetime.now())
	exportCaseDictToCSV(cases)

def exportCasesPreviousMonth():
	cases = getCasesForMonth(datetime.datetime.now() - datetime.timedelta(days=28))
	exportCaseDictToCSV(cases)

def exportAllCases():
	# cannot find the 'all' criteria for search method (other than accessing
	# _TheHiveApi__find_rowsfind_rows method directly, so using a criterion
	# that will be true for all cases
	cases = customParseJson(search("All Cases",Gte('severity', 1), 'all', []))
	exportCaseDictToCSV(cases)

#exportCasesCurrentWeeklyReportingPeriod()
#exportCasesPreviousWeeklyReportingPeriod()
#exportCasesMonthToDate()
#exportCasesPreviousMonth()
exportAllCases()