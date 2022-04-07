# add a check to see which network is more specific in registration
# add a filter to rule out common non-specific hosting provider registrations (maybe only add these as a /32)
# find a way to initiate an RDP login from linux host with a known username or IP, then surface AIE rule for it (maybe a generic rule for RDP from public internet)
# find a way to print RDP attempt status, and WHOIS registration, in STDOUT
# find a way to include S1 workstations
# find a way to include bitsight
# consider whitelisting registrations (e.g. GCP)

from ipwhois import IPWhois
import ipaddress

#IPS =['38.126.174.2','38.126.174.11','184.150.227.68','216.13.234.66','38.126.174.5','38.126.174.160','38.126.174.4','38.126.174.111','38.126.174.161','38.126.174.221','38.126.174.42','38.126.174.163','8.8.243.12','199.227.131.194','170.65.101.92','170.65.74.12','170.65.94.12','32.42.23.161','170.65.248.12','32.60.40.254','203.43.47.98','170.65.128.232','52.5.21.61','203.43.46.2','8.40.143.253','104.156.40.80','170.65.188.1','54.233.121.65','52.1.55.208','104.156.41.70','170.65.95.11','42.159.159.120','104.156.40.79','52.24.170.182','104.156.41.80','139.219.136.82','139.219.141.78','139.219.137.222','52.50.1.172','139.219.137.235','52.6.183.74','52.208.19.245','52.1.30.74','139.219.129.159','52.27.155.193','40.72.155.171','34.208.61.172','34.247.86.121','204.64.62.132','104.156.40.70','54.152.56.122','42.159.156.241','42.159.158.122','52.25.18.184','54.207.111.27','42.159.159.50','139.219.133.102','52.7.158.164','104.156.41.79','35.238.204.192','42.159.156.94','54.184.107.175','199.227.131.223','139.219.129.100','54.207.10.19','54.69.36.179','139.219.141.80','52.30.51.101','52.4.157.204','52.4.152.181','139.219.133.208','35.224.208.197','42.159.156.60','18.229.136.3','42.159.154.246','54.233.150.131','139.219.132.61','35.238.15.107','35.222.25.106','168.215.186.2','97.105.24.194','8.40.143.21','8.40.143.24','8.40.143.30','8.40.143.20','8.40.143.104','8.40.143.25','8.40.143.26','8.40.143.100','8.40.143.22','8.40.143.27','8.40.143.28','8.40.143.254','8.40.143.252','8.40.143.23','8.40.143.35','8.40.143.37','4.16.222.188','8.40.143.36','8.40.143.31','8.40.143.110','8.40.143.32','4.78.13.106','8.40.143.33','4.16.222.189','8.40.143.38','210.4.99.186','115.110.96.81','170.65.88.12','170.65.88.103','170.65.88.102','170.65.88.100','170.65.88.101','170.65.88.113','170.65.88.114','170.65.88.115','170.65.88.116','170.65.88.119','170.65.88.118','170.65.88.117','170.65.88.120','170.65.88.121','170.65.88.123','170.65.89.6','170.65.218.7','170.65.88.74','170.65.88.73','170.65.88.78','170.65.88.70','170.65.88.88','170.65.88.86','170.65.88.89','170.65.88.82','170.65.88.72','170.65.88.81','170.65.88.80','170.65.88.76','170.65.88.84','170.65.88.83','170.65.204.4','207.107.208.137','170.65.204.148']

IPS =['38.126.174.2','38.126.174.11','184.150.227.68','216.13.234.66']

# enter ports list as a string, per 'man masscan'
PORTS = '3389'

REGISTRATION_LIST = []
KNOWN_SUBNETS = []

def check_if_subnet_known(target_ip,list_of_subnets):
	this_ip = ipaddress.ip_address(target_ip)
	for subnet in list_of_subnets:
		if this_ip in subnet:
			return True
	return False

def export_registrations_to_csv(input_registrations_list):
	pass

for ip in IPS:
	if not check_if_subnet_known(ip,KNOWN_SUBNETS):
		registration = IPWhois(ip).lookup_rdap()
		REGISTRATION_LIST.append(registration)
		print(registration)
		input("Press any key to continue")
		this_subnet = ipaddress.IPv4Network(registration['network']['cidr'])
		KNOWN_SUBNETS.append(this_subnet)

for subnet in KNOWN_SUBNETS:
	print(subnet)
	#print(f'range = {registration["asn_cidr"]}')
print(f'ports = {PORTS}')
	