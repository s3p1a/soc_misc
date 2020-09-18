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
import pathlib
import argparse
# for email notifications
import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

# to do:
# - make weekly reporting period start/end configurable with global variable
#	by adjusting getStartOfWeeklyReportingPeriod() and
#	getEndOfWeeklyReportingPeriod()

# note: to run this as a cron job while using an anaconda environment, use

# https://unix.stackexchange.com/questions/454957/cron-job-to-run-under-conda-virtual-environment

THE_HIVE_URL = 'http://x.x.x.x:9000'
THE_HIVE_API_KEY = 'key'
API = TheHiveApi(THE_HIVE_URL, THE_HIVE_API_KEY)
SMTP_SERVER='server.example.com'
SMTP_DEFAULT_SEND_FROM='example@example.com'
SMTP_DEFAULT_SEND_TO=['example@example.com',] # needs to be a list, even if single address
HOST_LOOKUP_ENABLED = True
PATH_TO_HOST_CSV = r'C:\Users\user\Desktop\example.csv'

# pre-populate a dictionary of user names, as only the user ID is present in case
# json. '_TheHiveApi__find_rows' is a way to access the __find_rows private method
# within the TheHiveApi class.
# See https://stackoverflow.com/questions/9145499/calling-private-function-within-the-same-class-python
# and https://www.geeksforgeeks.org/name-mangling-in-python/ for additional details
USER_DICT = {item['id']:item['name'] for item in API._TheHiveApi__find_rows('/api/user/_search').json()}

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
		# post processing to convert user ID to display name
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
	},
	{
		'jsonField':'businessSegment',
		'displayName':'Business Segment',
		'isCustom':True,
		'postProcessing':None,
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	},
		{
		'jsonField':'businessUnit',
		'displayName':'Business Unit',
		'isCustom':True,
		'postProcessing':None,
		'functionOnPostProcessingException':None,
		'valueOnPostProcessingException':None,
	}
]

# search query syntax https://github.com/TheHive-Project/TheHive4py/blob/master/thehive4py/query.py
# from examples at https://github.com/TheHive-Project/TheHive4py/blob/master/samples/test-case-search.py
def search(title, query, range, sort):
	#print(title)
	#print('-----------------------------')
	response = API.find_cases(query=query, range=range, sort=sort)

	if response.status_code == 200:
		jsonResponse = response.json()
		#print(json.dumps(jsonResponse, indent=4, sort_keys=True))
		#print('')
	else:
		print('ko: {}/{}'.format(response.status_code, response.text))
		sys.exit(0)
	return jsonResponse

def hostListLookup(headers, caseList, pathToHostCSV=PATH_TO_HOST_CSV):
	# this method is used to append a 'Asset List Matches' column to the data pulled from
	# thehive's API, and is called by the getCasesByTimeWindow function
	
	# parse a CSV into a dict of 'hostname':'asset list' pairs
	with open(pathToHostCSV, mode='r') as csv_file:
		# read first line of csv file, split by comma, store as list
		firstline = csv_file.readline().strip().replace('"','').split(',')
		# reset file reader position to 0
		csv_file.seek(0)
		# test whether the expected column header is present
		if not (firstline[0] == 'Hostname' and firstline[1] == 'Asset List'):
			print('Error parsing critical assets list')
			print("Please ensure CSV has column headers ['Hostname', 'Asset List', ... ]")
			raise SystemExit
		csv_reader = csv.DictReader(csv_file)
		# this will convert all system names to hostname only (no FQDNs)
		hostListDict = {row['Hostname'].split('.')[0]:row['Asset List'] for row in csv_reader}
	systemsStringIndex = headers.index('Systems')
	for case in caseList:
		# if multiple systems in a case, expand them to an array
		thisSystemString = case[systemsStringIndex]
		thisSystemString =  thisSystemString.replace('and',',')
		thisSystemString = thisSystemString.replace(' ','')
		thisSystemString = thisSystemString.replace(',,',',')
		thisSystemsList = thisSystemString.split(',')
		# convert all system strings to hostname only
		thisSystemsList = list(map(lambda x: x.split('.')[0], thisSystemsList))
		# define host list matches as a set to prevent duplicates
		thisHostListMatches = set()
		for system in thisSystemsList:
			# check if this host is in the hostListDict
				if system in hostListDict.keys():
					thisHostListMatches.add(hostListDict[system])
		case.append(', '.join(thisHostListMatches))
	headers.append('Asset List Matches')
	return(headers,caseList)

def customParseJson(thisJson, fields=CASE_FIELDS_TO_PARSE):
	headers = []
	for field in CASE_FIELDS_TO_PARSE:
		headers.append(field['displayName'])
	caseList = []
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
		caseList.append(thisList)
	# this sort will only work when sorting by opened time, and it is in column 5
	# print(caseList)
	caseList.sort(key = lambda x:datetime.datetime.strptime(x[5],'%m/%d/%Y'),reverse=True)
	if HOST_LOOKUP_ENABLED:
		headers, caseList = hostListLookup(headers, caseList)
	return {'headers':headers,'caseList':caseList}

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

def exportCaseDictToCSV(caseDict,basePath=(pathlib.Path.home()/'Desktop')):
	# use pathlib to generate home directory path for easier cross-platform support
	# join basePath to CSV filename format
	# check if report is time-bound, and append start/end if so
	if 'startDatetime' in caseDict.keys():
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
	# return path for use in email reporting
	return(fullPath)

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
	# return path for use in email reporting
	return(exportCaseDictToCSV(cases))
	
def exportCasesPreviousWeeklyReportingPeriod():
	cases = getCasesWeeklyReportingPeriod(datetime.datetime.now() - datetime.timedelta(days=7))
	# return path for use in email reporting
	return(exportCaseDictToCSV(cases))

def exportCasesCurrentMonth():
	cases = getCasesForMonth(datetime.datetime.now())
	# return path for use in email reporting
	return(exportCaseDictToCSV(cases))

def exportCasesPreviousMonth():
	cases = getCasesForMonth(datetime.datetime.now() - datetime.timedelta(days=28))
	# return path for use in email reporting
	return(exportCaseDictToCSV(cases))

def exportCasesAll():
	# cannot find the 'all' criteria for search method (other than accessing
	# _TheHiveApi__find_rowsfind_rows method directly, so using a criterion
	# that will be true for all cases
	cases = customParseJson(search("All Cases",Gte('severity', 1), 'all', []))
	# return path for use in email reporting
	return(exportCaseDictToCSV(cases))

def exportCasesToday():
	startDatetime = datetime.datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
	endDatetime = datetime.datetime.now()
	cases = getCasesByTimeWindow(startDatetime,endDatetime)
	# return path for use in email reporting
	return(exportCaseDictToCSV(cases))

# https://stackoverflow.com/questions/3362600/how-to-send-email-attachments
# note that send_to is a list, if a raw string is passed it will add a comma between
# every character in the string passed
def send_mail(send_from=SMTP_DEFAULT_SEND_FROM, send_to=SMTP_DEFAULT_SEND_TO, subject='TheHive Case Report(s)', text='TheHive Case Report(s) attached', files=None,server=SMTP_SERVER):

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for f in files or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(f)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)


    smtp = smtplib.SMTP(server)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()


#note that action='store_true' creates an implicit value of false
parser = argparse.ArgumentParser("Export cases from TheHive as csv. Options can be combined")
parser.add_argument('-t','--today',action='store_true',help='Export cases for the current day')
parser.add_argument('-cw','--currentweek',action='store_true',help='Export cases for the current weekly reporting period')
parser.add_argument('-pw','--previousweek',action='store_true',help='Export cases for the previous weekly reporting period')
parser.add_argument('-cm','--currentmonth',action='store_true',help='Export cases for the current month')
parser.add_argument('-pm','--previousmonth',action='store_true',help='Export cases for the previous month')
parser.add_argument('-a','--all',action='store_true',help='Export all cases')
parser.add_argument('-n','--nolookup',action='store_true',help='Do not lookup cases against a systems list')
parser.add_argument('-e','--email',action='store_true',help='Email exported cases')
parser.add_argument('-r','--remove',action='store_true',help='Remove exported CSV files (for use when emailing reports)')
args = parser.parse_args()


#send_mail()

if not len(sys.argv) > 1:
	print('No arguments passed. Please select an option.')
	parser.print_help()
	raise SystemExit
	
if args.nolookup:
	HOST_LOOKUP_ENABLED = False

if args.email:
	emailFileList = []

if args.today:
	caseCSV = exportCasesToday()
	if args.email:
		emailFileList.append(caseCSV)

if args.currentweek:
	caseCSV = exportCasesCurrentWeeklyReportingPeriod()
	if args.email:
		emailFileList.append(caseCSV)
		
if args.previousweek:
	caseCSV = exportCasesPreviousWeeklyReportingPeriod()
	if args.email:
		emailFileList.append(caseCSV)

if args.currentmonth:
	caseCSV = exportCasesCurrentMonth()
	if args.email:
		emailFileList.append(caseCSV)	

if args.previousmonth:
	caseCSV = exportCasesPreviousMonth()
	if args.email:
		emailFileList.append(caseCSV)	
if args.all:
	caseCSV = exportCasesAll()
	if args.email:
		emailFileList.append(caseCSV)

if args.email:
	send_mail(files=emailFileList)
	if args.remove:
		for file in emailFileList:
			try:
				os.remove(file)
			except:
				print(f'File {file} could not be removed')
				continue
			print(f'File {file} removed successfully')