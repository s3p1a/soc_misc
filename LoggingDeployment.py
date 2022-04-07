import csv
import os
import datetime
import re
import pathlib
from collections import defaultdict
import uuid
import sys
# for API requests
import requests
import urllib3
import json
# for tracing API requests
import logging
# for email reporting
import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate

#### debug tools
# uncomment this to log all requests
#logging.basicConfig(level=logging.DEBUG)

# to do
# allow boolean search to use multiple statements
# finish implementing importFromHostNameFile, maybe adjust methods to allow a tag to be added to include where they came from > add a dynamic tag field to deployment, then
# 	automatically include that in the exportDeploymentToCSV function

#some examples of how this might be instantiated from an external script
#### populate data from various CSV sources
#myDeployment.importCSVFromAgentPropertiesExport(LR_SYSTEM_MONITORS_PATH)
#myDeployment.importCSVFromPendingAgentPropertiesExport(LR_SYSTEM_MONITORS_PENDING_PATH)
#myDeployment.importCSVFromLogSourcePropertiesExport(LR_LOG_SOURCES_PATH)
#myDeployment.importCSVFromPendingLogSourcePropertiesExport(LR_LOG_SOURCES_PENDING_PATH)
#myDeployment.importFromHostnameList(HOSTS_TO_CHECK)
#### populate from various CSV sources
#myBaseURL = 'https://<IP>:8501/lr-admin-api/'
#myApiToken = <TOKEN>
#myDeployment = LoggingDeployment()
#myDeployment.initializeAPIClient(apiAuthToken=myApiToken,apiBaseURL=myBaseURL)
#myDeployment.importFromAgentsAPI()
#myDeployment.importFromPendingAgentsAPI()
#myDeployment.importFromLogSourcesAPI()
#myDeployment.importFromPendingLogSourcesAPI()
#### print each host in deployment to console, including only selected fields (preserves order)
#myDeployment.printDeployment(attributesToInclude=['windowsApplicationLastLog', 'overallWithinCutoff'])
#### export a csv representation of deployment, including only selected fields (preserves order)
#myDeployment.exportDeploymentToCSV(OUTPUT_PATH,attributesToInclude=['systemMonitorGUIDs','hostname'])
#### return hosts where hostname contains substring 'LRCL', then print all data to console where each host is delimited by a string
#filteredDeployment = myDeployment.getDeploymentWithAttributeSubstring('hostname','LRCL')
#filteredDeployment.printDeployment(includeAttributePrefixes=True,delmeter='END OF HOST INFORMATION')
#### return only a list of hostnames that have checked in within cutoff
#deploymentWithinCutoff = myDeployment.getDeploymentWithinCutoff(CUTOFF_TIME)
#deploymentWithinCutoff.printDeployment(attributesToInclude=['hostname'],includeAttributePrefixes=False)
#### return only the subset of the deployment where hosts match a custom filter (e.g. passed in via lambda or function object)
#filteredDeployment = myDeployment.getDeploymentWithCustomFilter(filterFunction=lambda x: True if re.match(r'.*LRCL.*',x.hostname) else False)
#### return only those hosts which are on input list
#restoredHosts = myDeployment.getDeploymentWithinHostnameList(restoredHostsList)
#### deployment stats/counters
#statsDict = myDeployment.getDeploymentStats()
#myDeployment.printDeploymentStats()
#emailDeploymentStats(send_from='example@example.com',send_to=['example@example.com'],text=myCSVDeployment.getDeploymentStats(),subject='LogRhythm Weekly Metrics',files=None,server='SMTP.EXAMPLE.COM')
#### various reporting functions, which return a tuple of hosts meeting specific criteria:
#myDeployment.getHostsMissingWindowsCoreLogs()
#myDeployment.getHostsMissingWindowsPowershellLogs()
#myDeployment.getWindowsHostsCollectedRemotely()
#myDeployment.getHostsWithPendingAgents()
#myDeployment.getHostsWithPendingLogSources()
#myDeployment.getHostsWithLateSystemMonitorHeartBeats()
#myDeployment.getHostsWithLateNonWindowsLogSources()
#### email reporting
# note the send_to expects a list, even if that's a list of one item
# note that the text= parameter of both methods below can accept the output of a reporting function and place it into the body of the message
# the attachmentsDict parameter of sendEmailReport() can be used to place the output of a reporting script (passed in as dict value) into an attachment named according
# to the dict key
#myDeployment.emailDeploymentStats(send_from='example@example.com',send_to=['example@example.com'],text=myCSVDeployment.getDeploymentStats(),subject='LogRhythm Weekly Metrics',server='smtp.example.com')
#myCSVDeployment.sendEmailReport(send_from='example@example.com',send_to=['example@example.com'],text='Reports attached',subject='LogRhythm Weekly Reports',server='smtp.example.com',attachmentsDict={'hostsWithLateSMAHeartbeats':myCSVDeployment.getHostsWithLateSystemMonitorHeartBeats()})
# include the CSV export of a deployment in reporting email
# note that the files parameter expects a list, even if there's only one item
#csvpath = myDeployment.exportDeploymentToCSV(r'C:\Users\example\Desktop\example.csv')
#myDeployment.emailDeploymentStats(send_from='example@example.com',send_to=['example@example.com'],text=myCSVDeployment.getDeploymentStats(),subject='LogRhythm Weekly Metrics',files=[csvpath],server=mySMTPServer)
# email all reports, attach deployment export csv, and include stats in email body
#myDeployment.emailAllReportsWithDeploymentExport(send_from='example@example.com',send_to=['example@example.com'],server='smtp.example.com',subject='LogRhythm Weekly Reporting')


class LoggingDeployment:
	IP_ADDRESS_PATTERN = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
	FQDN_PATTERN = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{0,62}[a-zA-Z0-9]\.)+[a-zA-Z]{2,63}$)')
	def normalizeHostname(inputHostname):
			# sometimes the input may be from a shared excel spreadsheet where people are putting notes,
			# e.g. 'HOSTNAME - Rebuilt already'
			intermediateHostname = re.sub(r'[\'\"\s]','',re.split(r'[(). ]',inputHostname)[0]).upper()
			
			# convert FQDNs to hostnames
			if re.match(LoggingDeployment.FQDN_PATTERN,intermediateHostname):
				print('fqdn matched')
				intermediateHostname = intermediateHostname.split('.')[0]
			#print(f'{inputHostname} > {intermediateHostname}')
			return intermediateHostname
	def isIterable(obj):
		# https://www.geeksforgeeks.org/how-to-check-if-an-object-is-iterable-in-python/
		try:
			iter(obj)
		except(TypeError):
			return False 
		return True

	class LoggingDeploymentAPIClient:
		# https://stackoverflow.com/questions/29931671/making-an-api-call-in-python-with-an-api-that-requires-a-bearer-token
		class LR_AUTH(requests.auth.AuthBase):
			def __init__(self, token):
				self.token = token
			def __call__(self, r):
				r.headers["authorization"] = "Bearer " + self.token
				return r
				
		def __init__(self,*args,**kwargs):
			urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
			self.authToken = kwargs.get('authToken',None)
			self.baseURL = kwargs.get('baseURL',None)
			self.authObject = kwargs.get('authObject',self.LR_AUTH(self.authToken))
		
		def getAllDataFromApiEndpoint(self,apiEndpoint):
			allItems = []
			requestURL = self.baseURL + apiEndpoint
			requestParamCount = 1000
			requestParamOffset = 0
			while True:
				thisURL = f'{requestURL}?count={requestParamCount}&offset={requestParamOffset}'
				r = requests.get(thisURL,auth=self.authObject,verify=False)
				thisJson = r.json()
				allItems.extend(thisJson)
				requestParamOffset += 1000
				if len(thisJson) < 1000:
					break
			return allItems

	class LoggedHost:
		def getHostData(self):
			# return a clean dictionary representation of host data, for use e.g. when printing or exporting to CSV
			# https://stackoverflow.com/questions/8137456/get-class-and-object-attributes-of-class-without-methods-and-builtins
			return {k:v for k,v in self.__dict__.items() if not k.startswith("__") and not callable(v) and not type(v) is staticmethod}
		def __str__(self):
			return str(self.getHostData())
		def checkIfCollectedRemotely(self):
			self.isCollectedRemotely = False
			if self.windowsApplicationLogCollectionHost:
				if self.windowsApplicationLogCollectionHost != self.hostname:
					self.isCollectedRemotely = True
			if self.windowsSecurityLogCollectionHost:
				if self.windowsSecurityLogCollectionHost != self.hostname:
					self.isCollectedRemotely = True
			if self.windowsSystemLogCollectionHost:
				if self.windowsSystemLogCollectionHost != self.hostname:
					self.isCollectedRemotely = True
			if self.windowsPowershellCollectionHost:
				if self.windowsPowershellCollectionHost != self.hostname:
					self.isCollectedRemotely = True
			if self.nonWindowsLogSourceCollectionHost:
				if self.nonWindowsLogSourceCollectionHost != self.hostname:
					self.isCollectedRemotely = True
			return self.isCollectedRemotely
		
		def checkIfWithinCutoff(self,inputCutoffDatetime):
			self.overallWithinCutoff = False
			if self.windowsApplicationLastLog:
				if self.windowsApplicationLastLog >= inputCutoffDatetime:
					self.windowsApplicationLogWithinCutoff = True
					self.overallWithinCutoff = True
			if self.windowsSecurityLastLog:
				if self.windowsSecurityLastLog >= inputCutoffDatetime:
					self.windowsSecurityLogWithinCutoff = True
					self.overallWithinCutoff = True
			if self.windowsSystemLastLog:
				if self.windowsSystemLastLog >= inputCutoffDatetime:
					windowsSystemLogWithinCutoff = True
					self.overallWithinCutoff = True
			if self.windowsPowershellLastLog:
				if self.windowsPowershellLastLog >= inputCutoffDatetime:
					self.windowsPowershellLogWithinCutoff = True
					self.overallWithinCutoff = True
			if self.systemMonitorLastHeartbeat:
				if self.systemMonitorLastHeartbeat >= inputCutoffDatetime:
					self.systemMonitorWithinCutoff = True
					self.overallWithinCutoff = True
			if self.nonWindowsLogSourceLastLog:
				if self.nonWindowsLogSourceLastLog >= inputCutoffDatetime:
					self.nonWindowsLogSourceWithinCutoff = True
					self.overallWithinCutoff = True
			return self.overallWithinCutoff
		
		def checkIfWindowsCoreSourcesReporting(self):
			if 'Windows' not in self.logHostMetaType:
				return None
			if (self.windowsApplicationLastLog is not None
				and self.windowsSecurityLastLog is not None
				and self.windowsSystemLastLog is not None):
				self.allWindowsCoreLogSourcesReporting = True
			else:
				self.allWindowsCoreLogSourcesReporting = False
			return self.allWindowsCoreLogSourcesReporting
			
		def checkIfWindowsPowershellReporting(self):
			if 'Windows' not in self.logHostMetaType:
				return None
			if self.windowsPowershellLastLog is not None:
				self.windowsPowershellLogReporting = True
			else:
				self.windowsPowershellLogReporting = False
			return self.windowsPowershellLogReporting
			
		def checkIfMultipleSystemMonitorGuids(self):
			if len(self.systemMonitorGUIDs) > 1:
				self.hasMultipleSystemMonitorGuids = True
			return self.hasMultipleSystemMonitorGuids

		# https://stackoverflow.com/questions/1098549/proper-way-to-use-kwargs-in-python
		def __init__(self,*args,**kwargs):
			self.hostname = kwargs.get('hostname',None)
			if self.hostname:
				self.hostname = LoggingDeployment.normalizeHostname(self.hostname)
			self.ipAddress = kwargs.get('ipAddress',None)
			self.entity = kwargs.get('entity',None)
			self.systemMonitorPending = kwargs.get('systemMonitorPending',None)
			self.logSourcePending = kwargs.get('logSourcePending',None)
			self.systemMonitorLogSourcesActive = kwargs.get('systemMonitorLogSourcesActive',None)
			self.systemMonitorLogSourcesInactive = kwargs.get('systemMonitorLogSourcesInactive',None)
			self.systemMonitorGUIDs = kwargs.get('systemMonitorGUIDs',set())
			
			# used to determine if WMI remote collection is used for this host
			self.windowsApplicationLogCollectionHost = kwargs.get('windowsApplicationLogCollectionHost',None)
			self.windowsSecurityLogCollectionHost = kwargs.get('windowsSecurityLogCollectionHost',None)
			self.windowsSystemLogCollectionHost = kwargs.get('windowsSystemLogCollectionHost',None)
			self.windowsPowershellCollectionHost = kwargs.get('windowsPowershellCollectionHost',None)
			self.nonWindowsLogSourceCollectionHost = kwargs.get('nonWindowsLogSourceCollectionHost',None)
			self.wefCollectionHost = kwargs.get('wefCollectionHost',None)
			
			# last timestamps
			self.windowsApplicationLastLog = kwargs.get('windowsApplicationLastLog',None)
			self.windowsSecurityLastLog = kwargs.get('windowsSecurityLastLog',None)
			self.windowsSystemLastLog = kwargs.get('self.windowsSystemLastLog',None)
			self.windowsPowershellLastLog = kwargs.get('windowsPowershellLastLog',None)	
			self.nonWindowsLogSourceLastLog = kwargs.get('nonWindowsLogSourceLastLog',None)	
			self.systemMonitorLastHeartbeat = kwargs.get('systemMonitorLastHeartbeat',None)
			self.WEFLastLog = kwargs.get('WEFLastLog',None)
			
			# has the host checked in within cutoff
			self.windowsApplicationLogWithinCutoff = kwargs.get('windowsApplicationLogWithinCutoff',None)
			self.windowsSecurityLogWithinCutoff = kwargs.get('windowsSecurityLogWithinCutoff',None)
			self.windowsSystemLogWithinCutoff = kwargs.get('windowsSystemLogWithinCutoff',None)
			self.windowsPowershellLogWithinCutoff = kwargs.get('windowsPowershellLogWithinCutoff',None)
			self.systemMonitorWithinCutoff = kwargs.get('systemMonitorWithinCutoff',None)
			self.nonWindowsLogSourceWithinCutoff = kwargs.get('nonWindowsLogSourceWithinCutoff',None)
			
			# Windows, linux, or other
			self.logHostMetaType = kwargs.get('logHostMetaType',set())
			
			# used for analysis/reporting logic
			self.overallWithinCutoff = kwargs.get('overallWithinCutoff',None)
			self.allWindowsCoreLogSourcesReporting = kwargs.get('allWindowsCoreLogSourcesReporting',None)
			self.windowsPowershellLogReporting = kwargs.get('windowsPowershellLogReporting',None)
			self.isCollectedRemotely = kwargs.get('isCollectedRemotely',False)
			self.isReportingAsLogSource = kwargs.get('isReportingAsLogSource',False)
			self.isReportingViaWEF = kwargs.get('isReportingViaWEF',False)
			self.hasMultipleSystemMonitorGuids = kwargs.get('hasMultipleSystemMonitorGuids',False)
			
		# use classmethods to provide various means of calling constructor - note this isn't used, but may have other use cases in the future?
		# https://stackoverflow.com/questions/682504/what-is-a-clean-pythonic-way-to-have-multiple-constructors-in-python
		# expects a dict as produced by csv_dictreader
		# @classmethod
		# def initFromAgentPropertiesExport(cls,inputDict):
		#	return cls(
		#		attribute = someValue
		#	)
		####
		#### END of LoggedHost class
		####
		
	def __init__(self,*args,**kwargs):
		# https://stackoverflow.com/questions/34819921/python-inner-class-is-not-defined
		self.allLoggedHosts = kwargs.get('allLoggedHosts',defaultdict(LoggingDeployment.LoggedHost))
		self.loggedHostIPs = kwargs.get('loggedHostIPs',defaultdict(lambda: defaultdict(str)))
		self.loggedHostHostnames = kwargs.get('loggedHostHostnames',defaultdict(lambda: defaultdict(str)))
		self.apiClient = kwargs.get('apiClient',None)
		self.agentIDToHostNameMapping = kwargs.get('agentIDToHostNameMapping',defaultdict(str))
		self.agentIDToHostNameMappingPopulated = kwargs.get('agentIDToHostNameMappingPopulated',False)
	
	def initializeAPIClient(self,apiAuthToken,apiBaseURL):
		self.apiClient = LoggingDeployment.LoggingDeploymentAPIClient(authToken=apiAuthToken,baseURL=apiBaseURL)
	
	def generateUUID(self):
		thisUUID = uuid.uuid4()
		while thisUUID in self.allLoggedHosts.keys():
			thisUUID = uuid.uuid4()
		return thisUUID
	
	def resolveUUIDFromInputDict(self,inputDict):
		thisHostnameUUID = None
		thisIPUUID = None
		
		# replacedToUseEntity
		#if 'hostname' in inputDict:
		#	if inputDict['hostname'] in self.loggedHostHostnames.keys():
		#		thisHostnameUUID = self.loggedHostHostnames[inputDict['hostname']]
		#if 'ipAddress' in inputDict:
		#	if inputDict['ipAddress'] in self.loggedHostIPs.keys():
		#		thisIPUUID = self.loggedHostIPs[inputDict['ipAddress']]

		if 'hostname' in inputDict:
			if inputDict['hostname'] in self.loggedHostHostnames[inputDict['entity']].keys():
				thisHostnameUUID = self.loggedHostHostnames[inputDict['entity']][inputDict['hostname']]
		if 'ipAddress' in inputDict:
			if inputDict['ipAddress'] in self.loggedHostIPs[inputDict['entity']].keys():
				thisIPUUID = self.loggedHostIPs[inputDict['entity']][inputDict['ipAddress']]

		
		if thisHostnameUUID and not thisIPUUID:
			thisUUID = thisHostnameUUID
		elif thisIPUUID and not thisHostnameUUID:
			thisUUID = thisIPUUID
		elif thisHostnameUUID and thisIPUUID:
			if thisHostnameUUID == thisIPUUID:
				thisUUID = thisHostnameUUID
			else:
				raise KeyError('Mismatched GUIDs found')
		else:
			thisUUID = None
		return thisUUID
	
	def writeHost(self,inputDict):
		thisUUID = self.resolveUUIDFromInputDict(inputDict)
		if not thisUUID:
			thisUUID = self.generateUUID()
		thisLoggedHost = self.allLoggedHosts[thisUUID]
		for k,v in inputDict.items():
			if isinstance(v,set):
				newValue = getattr(thisLoggedHost,k).union(v)
				setattr(thisLoggedHost,k,newValue)
			elif isinstance(v,list):
				newValue = getattr(thisLoggedHost,k).extend(v)
				setattr(thisLoggedHost,k,newValue)
			elif isinstance(v,dict):
				newValue = getattr(thisLoggedHost,k)
				newValue = {**newValue, **k}
				setattr(thisLoggedHost,k,newValue)
			# only keep the most recent timestamp, for instance with use by WEF export
			elif isinstance(v,datetime.datetime):
				if getattr(thisLoggedHost,k) is not None:
					if getattr(thisLoggedHost,k) >= v:
						continue
				else:
					setattr(thisLoggedHost,k,v)
			else:
				setattr(thisLoggedHost,k,v)
		thisLoggedHost.checkIfCollectedRemotely()
		thisLoggedHost.checkIfWindowsCoreSourcesReporting()
		thisLoggedHost.checkIfWindowsCoreSourcesReporting()
		thisLoggedHost.checkIfMultipleSystemMonitorGuids()
		# replacedToUseEntity
		#if 'hostname' in inputDict:
		#	self.loggedHostHostnames[inputDict['hostname']] = thisUUID
		#if 'ipAddress' in inputDict:
		#	self.loggedHostIPs[inputDict['ipAddress']] = thisUUID
		if 'hostname' in inputDict:
			self.loggedHostHostnames[inputDict['entity']][inputDict['hostname']] = thisUUID
		if 'ipAddress' in inputDict:
			self.loggedHostIPs[inputDict['entity']][inputDict['ipAddress']] = thisUUID
		return thisUUID
		
	def writeHostFromHostname(self,inputHostname):
		thisDict = {}
		thisDict['hostname'] = LoggingDeployment.normalizeHostname(inputHostname)
		if len(thisDict['hostname']) < 1:
			return
		self.writeHost(thisDict)
	def writeFromAgentsAPI(self,inputDict,excludeRetired=True):
		# use this to catch inbound json for review
		#input(json.dumps(inputDict,indent=4))
		
		if excludeRetired:
			if inputDict['recordStatusName'] == 'Retired':
				return

		# map input metadata to metadata fields defined in LoggedHost object, then pass to generic write method
		thisDict = {}
		thisDict['logHostMetaType'] = set()
		thisDict['systemMonitorGUIDs'] = set()
		thisDict['hostname'] = LoggingDeployment.normalizeHostname(inputDict['hostName'])
		thisDict['logHostMetaType'].add(inputDict['os'])
		try:
			thisDict['systemMonitorLogSourcesActive'] = inputDict['activeLogSources']
		except KeyError:
			thisDict['systemMonitorLogSourcesActive'] = 0
		try: 
			thisDict['systemMonitorLogSourcesInactive'] = inputDict['inActiveLogSources']
		except KeyError:
			thisDict['systemMonitorLogSourcesInactive'] = 0
		try:
			thisDict['systemMonitorLastHeartbeat'] = datetime.datetime.strptime(inputDict['lastHeartbeat'].strip('Z'),"%Y-%m-%dT%H:%M:%S")
		except KeyError:
			thisDict['systemMonitorLastHeartbeat'] = None
		thisDict['systemMonitorGUIDs'].add(inputDict['guid'])
		thisDict['entity'] = inputDict['hostEntity']
		thisDict['isReportingAsLogSource'] = True
		self.writeHost(thisDict)
		# this is necessary to ID collection log host when parsing log sources
		self.agentIDToHostNameMapping[inputDict['id']] = thisDict['hostname']
	def writeFromPendingAgentsAPI(self,inputDict,excludeRejected=True):
		# use this to catch inbound json for review
		#input(json.dumps(inputDict,indent=4))
		
		if excludeRejected:
			if inputDict['acceptanceStatus'] == 'Rejected':
				return
		thisDict = {}
		thisDict['logHostMetaType'] = set()
		thisDict['systemMonitorGUIDs'] = set()
		thisDict['hostname'] = LoggingDeployment.normalizeHostname(inputDict['hostName'])		
		thisDict['logHostMetaType'].add(inputDict['agentType'].split(',')[0])
		thisDict['systemMonitorGUIDs'].add(inputDict['guid'])
		thisDict['systemMonitorPending'] = True
		#thisDict['isReportingAsLogSource'] = True
		thisDict['ipAddress'] = inputDict['ipAddress']
		thisDict['entity'] = 'Pending'
		self.writeHost(thisDict)
		# this is necessary to ID collection log host when parsing log sources
		self.agentIDToHostNameMapping[inputDict['id']] = thisDict['hostname']
	def writeFromLogSourcesAPI(self,inputDict,excludeRetired=True):
		# use this to catch inbound json for review
		#input(json.dumps(inputDict,indent=4))
		
		if excludeRetired:
			if inputDict['recordStatus'] == 'Retired':
				return
		
		# shim to exclude these log source types that we don't care about for now
		if inputDict['logSourceType']['name'] in {'LogRhythm Registry Integrity Monitor','LogRhythm Process Monitor (Windows)','LogRhythm File Monitor (Windows)','LogRhythm Data Loss Defender','LogRhythm Network Connection Monitor (Windows)','LogRhythm User Activity Monitor (Windows)','LogRhythm Filter','Flat File - Microsoft Netlogon','MS Windows Event Logging XML - Forwarded Events','MS Windows Event Logging XML - Sysmon 8/9/10'}:
			return
		thisDict = {}
		thisDict['logHostMetaType'] = set()
		thisDict['systemMonitorGUIDs'] = set()
		
		# this field is only present for syslog log sources, may be able to pull an IP address
		# even in cases where the log source name is hostname only but using logSourceIdentifiers
		if 'logSourceIdentifiers' in inputDict.keys():
			for identifier in inputDict['logSourceIdentifiers']:
				if identifier['type'] == "IPAddress":
					thisDict['ipAddress'] = identifier['value']
				else:
					thisDict['hostname'] = LoggingDeployment.normalizeHostname(identifier['value'])
		
		# log name may contain info that's not otherwise populated in logSourceIdentifiers (e.g. for a 
		# non-syslog log source, or for log sources where reverse DNS lookups were performed. In these cases,
		# we trust DNS less than we trust the logSourceIdentifiers, so we'll only populate hostnames if they
		# aren't already populated
		if re.match(LoggingDeployment.IP_ADDRESS_PATTERN,inputDict['host']['name']):
			if 'ipAddress' not in thisDict.keys():
				thisDict['ipAddress'] = inputDict['host']['name']
		else:
			if 'hostname' not in thisDict.keys():
				thisDict['hostname'] = LoggingDeployment.normalizeHostname(inputDict['host']['name'])

		# used to check whether the collection host is different that the logged host
		thisCollectionHostHostname = self.agentIDToHostNameMapping[inputDict['systemMonitorId']]
		
		# unlike the CSV export, the API will return a default timestamp if a log source has never
		# reported. For consistency, we'll replace with None
		if inputDict['maxLogDate'] == '1900-01-01T00:00:00Z':
			thisLastLogDate = None
		else:
			thisLastLogDate = datetime.datetime.strptime(inputDict['maxLogDate'].strip('Z').split('.')[0],'%Y-%m-%dT%H:%M:%S')
		
		if inputDict['logSourceType']['name'] in ['MS Windows Event Logging XML - Application','MS Event Log for XP/2000/2003 - Application']:
			thisDict['windowsApplicationLogCollectionHost'] = thisCollectionHostHostname
			thisDict['windowsApplicationLastLog'] = thisLastLogDate
			thisDict['logHostMetaType'].add('Windows')
			thisDict['isReportingAsLogSource'] = True
		elif inputDict['logSourceType']['name'] in ['MS Windows Event Logging XML - Security','MS Event Log for XP/2000/2003 - Security']:
			thisDict['windowsSecurityLogCollectionHost'] = thisCollectionHostHostname
			thisDict['windowsSecurityLastLog'] = thisLastLogDate
			thisDict['logHostMetaType'].add('Windows')
			thisDict['isReportingAsLogSource'] = True
		elif inputDict['logSourceType']['name'] in ['MS Windows Event Logging XML - System','MS Event Log for XP/2000/2003 - System']:
			thisDict['windowsSystemLogCollectionHost'] = thisCollectionHostHostname
			thisDict['windowsSystemLastLog'] = thisLastLogDate
			thisDict['logHostMetaType'].add('Windows')
			thisDict['isReportingAsLogSource'] = True
		elif inputDict['logSourceType']['name'] == 'MS Windows Event Logging - PowerShell':
			thisDict['windowsPowershellCollectionHost'] = thisCollectionHostHostname
			thisDict['windowsPowershellLastLog'] = thisLastLogDate
			thisDict['logHostMetaType'].add('Windows')
			thisDict['isReportingAsLogSource'] = True
		elif re.match(r'.*Linux.*',inputDict['logSourceType']['name']):
			thisDict['nonWindowsLogSourceCollectionHost'] = thisCollectionHostHostname
			thisDict['nonWindowsLogSourceLastLog'] = thisLastLogDate
			thisDict['logHostMetaType'].add('Linux')
			thisDict['isReportingAsLogSource'] = True
		else:
			thisDict['nonWindowsLogSourceCollectionHost'] = thisCollectionHostHostname
			thisDict['nonWindowsLogSourceLastLog'] = thisLastLogDate
			thisDict['logHostMetaType'].add(inputDict['logSourceType']['name'])
			thisDict['isReportingAsLogSource'] = True
		thisDict['entity'] = inputDict['entity']['name']
		self.writeHost(thisDict)

	def writeFromPendingLogSourcesAPI(self,inputDict,excludeRejected=True):
		# use this to catch inbound json for review
		#input(json.dumps(inputDict,indent=4))
		if excludeRejected:
			if inputDict['acceptanceStatus'] == 'Rejected':
				return
		thisDict = {}
		thisDict['ipAddress'] = inputDict['ip']
		thisDict['logSourcePending'] = True
		thisDict['entity'] = 'Pending'
		self.writeHost(thisDict)
	def importFromAgentsAPI(self):
		if self.apiClient is None:
			print('API client has not been initialized')
			print('Initalize client with \'myDeployment.initializeAPIClient(apiAuthToken=myApiToken,apiBaseURL=myBaseURL)\'')
			raise RuntimeError
		else:
			allAgents = self.apiClient.getAllDataFromApiEndpoint('agents/')
			for agent in allAgents:
				self.writeFromAgentsAPI(agent)
			self.agentIDToHostNameMappingPopulated = True
	def importFromPendingAgentsAPI(self):
		if self.apiClient is None:
			print('API client has not been initialized')
			print('Initalize client with \'myDeployment.initializeAPIClient(apiAuthToken=myApiToken,apiBaseURL=myBaseURL)\'')
			raise RuntimeError
		else:
			allPendingAgents = self.apiClient.getAllDataFromApiEndpoint('agents-request/')
			for agent in allPendingAgents:
				self.writeFromPendingAgentsAPI(agent)
			self.agentIDToHostNameMappingPopulated = True
	def importFromLogSourcesAPI(self):
		if self.apiClient is None:
			print('API client has not been initialized')
			print('Initalize client with \'myDeployment.initializeAPIClient(apiAuthToken=myApiToken,apiBaseURL=myBaseURL)\'')
			raise RuntimeError
		else:
			# this method depends on a mapping of agent IDs to hostnames in order to determine if the log source
			# is collected remotely, thus we'll make sure the dictionary has been populated before proceeding
			# note that pending agents do not have log sources, so we only care about accepted agents
			if not self.agentIDToHostNameMappingPopulated:
				allAgents = self.apiClient.getAllDataFromApiEndpoint('agents/')
				for agent in allAgents:
					self.agentIDToHostNameMapping[agent['id']] = LoggingDeployment.normalizeHostname(agent['hostName'])
				self.agentIDToHostNameMappingPopulated = True
			allLogSources = self.apiClient.getAllDataFromApiEndpoint('logsources/')
			for logSource in allLogSources:
				self.writeFromLogSourcesAPI(logSource)
	def importFromPendingLogSourcesAPI(self):
		if self.apiClient is None:
			print('API client has not been initialized')
			print('Initalize client with \'myDeployment.initializeAPIClient(apiAuthToken=myApiToken,apiBaseURL=myBaseURL)\'')
			raise RuntimeError
		else:
			allPendingLogSources = self.apiClient.getAllDataFromApiEndpoint('logsources-request/')
			for logSource in allPendingLogSources:
				self.writeFromPendingLogSourcesAPI(logSource)

	def writeFromAgentPropertiesExport(self,inputDict):
		# map input metadata to metadata fields defined in LoggedHost object, then pass to generic write method
		thisDict = {}
		thisDict['logHostMetaType'] = set()
		thisDict['systemMonitorGUIDs'] = set()
		thisDict['hostname'] = LoggingDeployment.normalizeHostname(inputDict['HostName'])
		thisDict['logHostMetaType'].add(inputDict['Type'])
		thisDict['systemMonitorLogSourcesActive'] = inputDict['LogSourcesActive']
		thisDict['systemMonitorLogSourcesInactive'] = inputDict['LogSourcesInactive']
		thisDict['systemMonitorLastHeartbeat'] = datetime.datetime.strptime(inputDict['LastHeartbeat'],'%m/%d/%Y %I:%M:%S.%f %p') if (inputDict['LastHeartbeat']) else None
		thisDict['systemMonitorGUIDs'].add(inputDict['Agent GUID'])
		thisDict['isReportingAsLogSource'] = True
		thisDict['entity'] = inputDict['Host Entity']
		self.writeHost(thisDict)
	def writeFromPendingAgentPropertiesExport(self,inputDict):
		thisDict = {}
		thisDict['logHostMetaType'] = set()
		thisDict['systemMonitorGUIDs'] = set()
		thisDict['hostname'] = LoggingDeployment.normalizeHostname(inputDict['Agent Name'])		
		thisDict['logHostMetaType'].add(inputDict['Host Operating System'].split(',')[0])
		thisDict['systemMonitorGUIDs'].add(inputDict['Agent GUID'])
		thisDict['systemMonitorPending'] = True
		#thisDict['isReportingAsLogSource'] = True
		thisDict['ipAddress'] = inputDict['Host IP Address']
		thisDict['entity'] = 'Pending'
		self.writeHost(thisDict)
	def writeFromLogSourcePropertiesExport(self,inputDict):
		# shim to exclude these log source types that we don't care about for now
		if inputDict['Log Source Type'] in {'LogRhythm Registry Integrity Monitor','LogRhythm Process Monitor (Windows)','LogRhythm File Monitor (Windows)','LogRhythm Data Loss Defender','LogRhythm Network Connection Monitor (Windows)','LogRhythm User Activity Monitor (Windows)','LogRhythm Filter','Flat File - Microsoft Netlogon','MS Windows Event Logging XML - Forwarded Events','MS Windows Event Logging XML - Sysmon 8/9/10'}:
			return
		thisDict = {}
		thisDict['logHostMetaType'] = set()
		thisDict['systemMonitorGUIDs'] = set()
		# this export lists both IPs and hostnames in the 'Log Host' column, so check which it is
		if re.match(LoggingDeployment.IP_ADDRESS_PATTERN,inputDict['Log Host']):
			thisDict['ipAddress'] = inputDict['Log Host']
		else:
			thisDict['hostname'] = LoggingDeployment.normalizeHostname(inputDict['Log Host'])
		if inputDict['Log Source Type'] in ['MS Windows Event Logging XML - Application','MS Event Log for XP/2000/2003 - Application']:
			thisDict['windowsApplicationLogCollectionHost'] = LoggingDeployment.normalizeHostname(re.split(r'Host: ',inputDict['Collection Host'])[1])
			thisDict['windowsApplicationLastLog'] = datetime.datetime.strptime(inputDict['Last Log Message'],'%m/%d/%Y %I:%M:%S.%f %p') if (inputDict['Last Log Message']) else None
			thisDict['logHostMetaType'].add('Windows')
			thisDict['isReportingAsLogSource'] = True
		elif inputDict['Log Source Type'] in ['MS Windows Event Logging XML - Security','MS Event Log for XP/2000/2003 - Security']:
			thisDict['windowsSecurityLogCollectionHost'] = LoggingDeployment.normalizeHostname(re.split(r'Host: ',inputDict['Collection Host'])[1])
			thisDict['windowsSecurityLastLog'] = datetime.datetime.strptime(inputDict['Last Log Message'],'%m/%d/%Y %I:%M:%S.%f %p') if (inputDict['Last Log Message']) else None
			thisDict['logHostMetaType'].add('Windows')
			thisDict['isReportingAsLogSource'] = True
		elif inputDict['Log Source Type'] in ['MS Windows Event Logging XML - System','MS Event Log for XP/2000/2003 - System']:
			thisDict['windowsSystemLogCollectionHost'] = LoggingDeployment.normalizeHostname(re.split(r'Host: ',inputDict['Collection Host'])[1])
			thisDict['windowsSystemLastLog'] = datetime.datetime.strptime(inputDict['Last Log Message'],'%m/%d/%Y %I:%M:%S.%f %p') if (inputDict['Last Log Message']) else None
			thisDict['logHostMetaType'].add('Windows')
			thisDict['isReportingAsLogSource'] = True
		elif inputDict['Log Source Type'] == 'MS Windows Event Logging - PowerShell':
			thisDict['windowsPowershellCollectionHost'] = LoggingDeployment.normalizeHostname(re.split(r'Host: ',inputDict['Collection Host'])[1])
			thisDict['windowsPowershellLastLog'] = datetime.datetime.strptime(inputDict['Last Log Message'],'%m/%d/%Y %I:%M:%S.%f %p') if (inputDict['Last Log Message']) else None
			thisDict['logHostMetaType'].add('Windows')
			thisDict['isReportingAsLogSource'] = True
		elif re.match(r'.*Linux.*',inputDict['Log Source Type']):
			thisDict['nonWindowsLogSourceCollectionHost'] = LoggingDeployment.normalizeHostname(re.split(r'Host: ',inputDict['Collection Host'])[1])
			thisDict['nonWindowsLogSourceLastLog'] = datetime.datetime.strptime(inputDict['Last Log Message'],'%m/%d/%Y %I:%M:%S.%f %p') if (inputDict['Last Log Message']) else None
			thisDict['logHostMetaType'].add('Linux')
			thisDict['isReportingAsLogSource'] = True
		else:
			thisDict['nonWindowsLogSourceCollectionHost'] = LoggingDeployment.normalizeHostname(re.split(r'Host: ',inputDict['Collection Host'])[1])
			thisDict['nonWindowsLogSourceLastLog'] = datetime.datetime.strptime(inputDict['Last Log Message'],'%m/%d/%Y %I:%M:%S.%f %p') if (inputDict['Last Log Message']) else None
			thisDict['logHostMetaType'].add(inputDict['Log Source Type'])
			thisDict['isReportingAsLogSource'] = True
		thisDict['entity'] = inputDict['Log Entity']
		self.writeHost(thisDict)
	def writeFromPendingLogSourcePropertiesExport(self,inputDict):
		if inputDict['Status'] == 'Rejected':
			return
		thisDict = {}
		# experimental - do we trust DNS?
		#if len(inputDict['Log Host Name']) > 0:
		#	thisDict['hostname'] = LoggingDeployment.normalizeHostname(inputDict['Log Host Name'])
		thisDict['ipAddress'] = inputDict['Device IP Address']
		thisDict['logSourcePending'] = True
		thisDict['entity'] = 'Pending'
		self.writeHost(thisDict)
	def writeFromWEFExport(self,inputDict):
		# unlike other import methods, WEF report contains many records from the same host, so there are multiple timestamps per host.
		# need to use a dedicated method to check timestamps and only keep the most recent
		thisDict = {}
		thisDict['hostname'] = LoggingDeployment.normalizeHostname(inputDict['hostname'])
		thisDict['WEFLastLog'] = datetime.datetime.strptime(inputDict['lastLog'],'%m/%d/%Y %I:%M %p')
		thisDict['logHostMetaType'] = 'Windows'
		thisDict['isReportingViaWEF'] = True
		thisDict['entity'] = inputDict['entity']
		thisDict['wefCollectionHost'] = LoggingDeployment.normalizeHostname(inputDict['wefCollectionHost'])
		self.writeHost(thisDict)
	def importFromHostnameList(self,inputList):
		for hostname in inputList:
			self.writeHostFromHostname(hostname)
	def importFromHostNameFile(self,filePath):
		pass
	def importCSVFromAgentPropertiesExport(self,csvPath):
		with open(csvPath) as csvFile:
			csvReader = csv.DictReader(csvFile)
			for asset in csvReader:
				self.writeFromAgentPropertiesExport(asset)
	def importCSVFromPendingAgentPropertiesExport(self,csvPath):
		with open(csvPath) as csvFile:
			csvReader = csv.DictReader(csvFile)
			for asset in csvReader:
				self.writeFromPendingAgentPropertiesExport(asset)
	def importCSVFromLogSourcePropertiesExport(self,csvPath):
		with open(csvPath) as csvFile:
			csvReader = csv.DictReader(csvFile)
			for asset in csvReader:
				self.writeFromLogSourcePropertiesExport(asset)
	def importCSVFromPendingLogSourcePropertiesExport(self,csvPath):
		with open(csvPath) as csvFile:
			csvReader = csv.DictReader(csvFile)
			for asset in csvReader:
				self.writeFromPendingLogSourcePropertiesExport(asset)
	def importCSVFromWEFExport(self,csvPath):
		with open(csvPath) as csvFile:
			# the first line of the WEF report seems to only report the collector itself, so skip it
			# must do this before the csvReader is instantiated per https://stackoverflow.com/questions/31031342/skipping-lines-csv-dictreader
			csvFile.readline()
			# the current WEF report does not contain headers, so we need to use position in the CSV file. We only care about the host
			# name and last log, so we assign every other column as none - this will cause all values from those colums to be appended to a list
			# object as a value in the dictionary indexed by dict key 'None'. We use none because that's what the dictReader defaults to for colums
			# without specified headers, such as those that follow the ones we're targeting
			# strange behavior, but we're discarding it all anyway and it stays local to this method
			fieldnames = [None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,'entity','wefCollectionHost','hostname','lastLog']
			csvReader = csv.DictReader(csvFile,fieldnames)
			for asset in csvReader:
				del asset[None]
				self.writeFromWEFExport(asset)
	def checkLoggedHostsAgainstCutoff(self,inputCutoffDatetime):
		# keep this for cases where we want to find hosts that have not reported since cutoff without removing from deployment
		# this method is necessary since the cutoff may not be known when the host information is written, so we can't include
		# this check in the writeHost() method
		for host in self.allLoggedHosts.values():
			host.checkIfWithinCutoff(inputCutoffDatetime)
	def getDeploymentWithinCutoff(self,inputCutoffDatetime):
		# note: can't set inputCutoffDatetime's default value with a class property:
		# https://stackoverflow.com/questions/52853793/use-class-self-variable-as-default-class-method-argument/52853918
		thisFilterFunction = lambda x: True if x.checkIfWithinCutoff(inputCutoffDatetime) == True else False
		return self.getDeploymentWithCustomFilter(thisFilterFunction)
	def getDeploymentWithinHostnameList(self,inputList):
		inputList = set([LoggingDeployment.normalizeHostname(hostname) for hostname in inputList])
		thisFilterFunction = lambda x: True if x.hostname in inputList else False
		return self.getDeploymentWithCustomFilter(thisFilterFunction)
	def getDeploymentWithAttributeSubstring(self,inputAttribute,inputString):
		# returns a subset of the deployment where hosts have a given substring in the given attribute
		# if the attribute is iterable, will try all elements of attribute
		def thisFilterFunction(inputHost):
			thisRegex = re.compile(rf'.*{inputString}.*')
			thisAttr = getattr(inputHost,inputAttribute)
			if LoggingDeployment.isIterable(thisAttr) and type(thisAttr) != str:
				thisResult = False
				try:
					for attribute in thisAttr:
						if thisRegex.match(attribute):
							thisResult = True
				except TypeError:
					return False
				return thisResult
			else:
				try:
					if thisRegex.match(thisAttr):
						return True
					else:
						return False
				except TypeError:
					return False
		return self.getDeploymentWithCustomFilter(thisFilterFunction)
	def getDeploymentWithAttributeBoolean(self,inputAttribute,inputBoolean):
		def thisFilterFunction(inputHost):
			try:
				if getattr(inputHost,inputAttribute) == inputBoolean:
					return True
				else:
					return False
			except TypeError:
				return False
		return self.getDeploymentWithCustomFilter(thisFilterFunction)
	def getDeploymentWithCustomFilter(self,filterFunction):
		# this is gnar - can return a subset of the deployment that matches an arbitrary lambda function, for example:
		# filteredDeployment = myDeployment.getDeploymentWithCustomFilter(filterFunction=lambda x: True if re.match(r'.*LRCL.*',x.hostname) else False)
		# or store a more complex function as a vriable and pass it in:
		# def LRCLFilter(x):
		#	collectors = ['USZYC-LRCL1','USZYC-LRCL2','USZYC-LRCL3','USZYC-LRCL4','USZYC-LRCL5']
		#	if x.hostname in collectors:
		#		return True
		#	else:
		#		return False
		# filteredDeployment = myDeployment.getDeploymentWithCustomFilter(filterFunction=LRCLFilter)
		filteredLoggedHosts = {k:v for k,v in self.allLoggedHosts.items() if filterFunction(v)}
		# rebuild nested dicts of hostname:guid and IP:guid mappings to only include filtered hosts
		# https://stackoverflow.com/questions/17915117/nested-dictionary-comprehension-python
		filteredLoggedHostIPs = {outer_entity: {inner_ip: inner_guid for inner_ip,inner_guid in outer_ip.items() if inner_guid in filteredLoggedHosts} for outer_entity,outer_ip in self.loggedHostIPs.items()}
		filteredLoggedHostIPs = {k:v for k,v in filteredLoggedHostIPs.items() if len(v) > 0}
		filteredLoggedHostHostnames = {outer_entity: {inner_hostname: inner_guid for inner_hostname,inner_guid in outer_hostname.items() if inner_guid in filteredLoggedHosts} for outer_entity,outer_hostname in self.loggedHostHostnames.items()}
		filteredLoggedHostHostnames = {k:v for k,v in filteredLoggedHostHostnames.items() if len(v) > 0}
		return LoggingDeployment(allLoggedHosts=filteredLoggedHosts,loggedHostIPs=filteredLoggedHostIPs,loggedHostHostnames=filteredLoggedHostHostnames,apiClient=self.apiClient)
	def getHostsMissingWindowsCoreLogs(self):
		windowsHostsMissingCoreLogs = [v.hostname for k,v in self.allLoggedHosts.items() if v.checkIfWindowsCoreSourcesReporting() == False and v.isReportingAsLogSource == True]
		# using a tuple so it can be placed into a dict and fed to sendEmailReport() - lists aren't hashable and can't be placed into a dict
		return tuple(windowsHostsMissingCoreLogs)
	def getHostsMissingWindowsPowershellLogs(self):
		windowsHostsMissingPowershellLogs = [v.hostname for k,v in self.allLoggedHosts.items() if v.checkIfWindowsPowershellReporting() == False and v.isReportingAsLogSource == True]
		return tuple(windowsHostsMissingPowershellLogs)
	def getWindowsHostsCollectedRemotely(self):
		windowsHostsCollectedRemotely = [v.hostname for k,v in self.allLoggedHosts.items() if v.checkIfCollectedRemotely() == True and 'Windows' in v.logHostMetaType]
		return tuple(windowsHostsCollectedRemotely)
	def getHostsWithPendingAgents(self):
		hostsWithPendingAgents = [v.hostname for k,v in self.allLoggedHosts.items() if v.systemMonitorPending == True]
		return tuple(hostsWithPendingAgents)
	def getHostsWithPendingLogSources(self):
		hostsWithPendingLogSources = [v.ipAddress for k,v in self.allLoggedHosts.items() if v.logSourcePending == True]
		return tuple(hostsWithPendingLogSources)
	def getHostsWithLateSystemMonitorHeartBeats(self,threshold=24):
		thresholdDatetime = datetime.datetime.now() - datetime.timedelta(hours=threshold)
		hostsWithLateSystemMonitorHeartBeats = [v.hostname for k,v in self.allLoggedHosts.items() if v.systemMonitorLastHeartbeat is not None and v.systemMonitorLastHeartbeat < thresholdDatetime]
		return tuple(hostsWithLateSystemMonitorHeartBeats)
	def getHostsWithLateNonWindowsLogSources(self,threshold=24):
		thresholdDatetime = datetime.datetime.now() - datetime.timedelta(hours=threshold)
		hostsWithLateNonWindowsLogSources = [v for k,v in self.allLoggedHosts.items() if v.nonWindowsLogSourceLastLog is not None and v.nonWindowsLogSourceLastLog < thresholdDatetime]
		# some have hostnames, some have IPs, so fix up here before returning
		hostsWithLateNonWindowsLogSources = [host.hostname if host.hostname is not None else host.ipAddress for host in hostsWithLateNonWindowsLogSources]
		return tuple(hostsWithLateNonWindowsLogSources)
	def getDeploymentStats(self):
		thisDict = {}
		thisDict['totalHosts'] = len(self.allLoggedHosts.keys())
		thisDict['windowHostsMissingCoreLogs'] = len(self.getHostsMissingWindowsCoreLogs())
		thisDict['windowHostsMissingPowershellLogs'] = len(self.getHostsMissingWindowsPowershellLogs())
		thisDict['windowsHostsCollectedRemotely'] = len(self.getWindowsHostsCollectedRemotely())
		thisDict['hostsWithPendingAgents'] = len(self.getHostsWithPendingAgents())
		thisDict['hostsWithPendingLogSources'] = len(self.getHostsWithPendingLogSources())
		thisDict['hostsWithLateSystemMonitorHeartBeats'] = len(self.getHostsWithLateSystemMonitorHeartBeats())
		thisDict['hostsWithLateNonWindowsLogSources'] = len(self.getHostsWithLateNonWindowsLogSources())
		return thisDict
	def printDeploymentStats(self):
		for k,v in self.getDeploymentStats().items():
			print(f'{k}: {v}')
	def flattenObjectToMIMEText(self,inputObj):
		if isinstance(inputObj,str):
			return MIMEText(inputObj)
		elif isinstance(inputObj,(list,set,tuple)):	
			thisString = ''
			for item in inputObj:
				thisString += item
				thisString += '\r\n'
			return(MIMEText(thisString))
		elif isinstance(inputObj,dict):
			thisString = ''
			for k,v in inputObj.items():
				thisString += f'{k}: {v}'
				thisString += '\r\n'
			return(MIMEText(thisString))	
		else:
			return None
	def sendEmailReport(self,send_from=None,send_to=None,subject=None,text=None,files=None,server=None,attachmentsDict=None):
		msg = MIMEMultipart()
		msg['From'] = send_from
		msg['To'] = COMMASPACE.join(send_to)
		msg['Date'] = formatdate(localtime=True)
		msg['Subject'] = subject
		
		msg.attach(self.flattenObjectToMIMEText(text))
		if not isinstance(send_to,list):
			raise TypeError('send_to must be a list, even if there is only one destination address')
		if attachmentsDict is not None:
			if not isinstance(attachmentsDict,dict):
				raise TypeError('attachmentsDict must be a dict of {attachmentName: object} pairs')
			for k,v in attachmentsDict.items():
				attachment = self.flattenObjectToMIMEText(v)
				attachment['Content-Disposition'] = f'attachment; filename={k}.txt'
				msg.attach(attachment)
		if files is not None:
			if not isinstance(files,list):
				raise TypeError('files must be a list, even if there is only one item')
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
	def emailDeploymentStats(self,send_from=None,send_to=None,subject=None,text=None,files=None,server=None,attachmentsDict=None):
		self.sendEmailReport(send_from=send_from,send_to=send_to,subject=subject,text=self.getDeploymentStats(),files=files,server=server,attachmentsDict=attachmentsDict)
	def emailAllReportsWithDeploymentExport(self,send_from=None,send_to=None,subject='LogRhythm Reporting',server=None):
		reportsDict = {}
		reportsDict['windowHostsMissingCoreLogs'] = self.getHostsMissingWindowsCoreLogs()
		reportsDict['windowHostsMissingPowershellLogs'] = self.getHostsMissingWindowsPowershellLogs()
		reportsDict['windowsHostsCollectedRemotely'] = self.getWindowsHostsCollectedRemotely()
		reportsDict['hostsWithPendingAgents'] = self.getHostsWithPendingAgents()
		reportsDict['hostsWithPendingLogSources'] = self.getHostsWithPendingLogSources()
		reportsDict['hostsWithLateSystemMonitorHeartBeats'] = self.getHostsWithLateSystemMonitorHeartBeats()
		reportsDict['hostsWithLateNonWindowsLogSources'] = self.getHostsWithLateNonWindowsLogSources()
		tempCSVPath = self.exportDeploymentToCSV(os.path.join(os.getcwd(),rf'LogRhythm_Deployment_{datetime.datetime.now().strftime("%m-%d-%Y")}.csv'))
		self.sendEmailReport(send_from=send_from,send_to=send_to,subject=subject,server=server,text=self.getDeploymentStats(),attachmentsDict=reportsDict,files=[tempCSVPath])
		os.remove(tempCSVPath)
	def printDeployment(self,attributesToInclude=[],includeAttributePrefixes=True,delimeter=''):
		# output preserves order of attributes specified in attributes to include
		if len(self.allLoggedHosts.values()) < 1:
			print('{WARNING] Deployment object is empty, please check any filters')
			return
		targetAttributes = list(self.allLoggedHosts.values())[0].getHostData().keys()
		if len(attributesToInclude) > 0:
			targetAttributes = [attribute for attribute in attributesToInclude if attribute in targetAttributes]
		for host in self.allLoggedHosts.values():
			for attribute in targetAttributes:
				if includeAttributePrefixes:
					print(f'{attribute}={getattr(host,attribute)}')
				else:
					print(getattr(host,attribute))
			if len(delimeter) > 0:
				print(delimeter)
	def exportDeploymentToCSV(self,exportPath,attributesToInclude=[]):
		# output preserves order of attributes specified in attributes to include
		# enumerate possible keys
		if len(self.allLoggedHosts.values()) < 1:
			print('{WARNING] Deployment object is empty, please check any filters')
			return
		targetAttributes = list(self.allLoggedHosts.values())[0].getHostData().keys()
		if len(attributesToInclude) > 0:
			targetAttributes = [attribute for attribute in attributesToInclude if attribute in targetAttributes]
		with open(exportPath, 'w', newline='') as outputFile:
			wr = csv.writer(outputFile, quoting=csv.QUOTE_ALL)
			wr.writerow(targetAttributes)
			for v in self.allLoggedHosts.values():
				thisRow = []
				for attribute in targetAttributes:
					# avoid printing object types for empty values (e.g. set() for systemMonitorGUIDs)
					if LoggingDeployment.isIterable(getattr(v,attribute)) and len(getattr(v,attribute)) == 0:
						thisRow.append('')
						continue
					thisRow.append(getattr(v,attribute))
				wr.writerow(thisRow)
		return exportPath