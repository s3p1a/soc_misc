import sys
from LoggingDeployment import LoggingDeployment
mySMTPFrom = 'logrhythmreporting@example.com'
mySMTPTo = ['example@example.com']
mySMTPServer = 'MAILGATEWAY.EXAMPLE.COM'
myBaseURL = 'https://EXAMPLE:8501/lr-admin-api/'
myApiToken = 'TOKEN'
WEF_EXPORT_PATH = r'D:\example.csv'
myAPIDeployment = LoggingDeployment()
myAPIDeployment.initializeAPIClient(apiAuthToken=myApiToken,apiBaseURL=myBaseURL)
myAPIDeployment.importFromAgentsAPI()
myAPIDeployment.importFromPendingAgentsAPI()
myAPIDeployment.importFromLogSourcesAPI()
myAPIDeployment.importFromPendingLogSourcesAPI()
myAPIDeployment.importCSVFromWEFExport(WEF_EXPORT_PATH)
myAPIDeployment.emailAllReportsWithDeploymentExport(send_from=mySMTPFrom,send_to=mySMTPTo,server=mySMTPServer)