from ipwhois import IPWhois
import csv
import pathlib
import os
import datetime
import ipaddress
import sys

input_list = ['45.23.0.208','87.202.24.246','180.190.130.164','131.226.43.44','205.172.134.229','136.158.7.247','103.99.8.137','49.206.57.178','34.99.86.190','103.149.37.177','208.127.153.79','136.158.46.37','130.105.195.221','134.238.161.95','203.192.203.58','208.127.239.23','136.158.1.16','180.194.243.25','198.203.177.177','209.146.16.114','119.93.167.4','134.238.161.94','136.158.57.23','168.215.186.2','152.32.100.100','50.72.72.227','49.144.63.199','206.85.94.117','174.50.120.218','103.82.210.46','112.205.56.69']

known_registrations = {}

def checkIfSubnetKnown(target_ip):
	target_ip = ipaddress.ip_address(target_ip)
	for subnet,registration in known_registrations.items():
		if target_ip in subnet:
			return registration
	return None

def get_registration(target_ip):
	this_registration = checkIfSubnetKnown(target_ip)
	if this_registration is None:
		try:
			this_registration = IPWhois(target_ip).lookup_rdap()
		except:
			print(f'Error performing WHOIS RDAP Lookup for {target_ip}')
			this_registration = {'asn_description': 'Error'}
			return this_registration
		try:
			this_subnet = ipaddress.IPv4Network(this_registration['asn_cidr'])
		except:
			print(f'Error parsing asn_cidr for {target_ip}')
			print(this_registration)
			sys.exit()
		known_registrations[this_subnet] = this_registration
	return this_registration
	
for ip in input_list:
	registration = get_registration(ip)
	print(f'{ip},{registration["asn_description"].split(",")[0]}')
