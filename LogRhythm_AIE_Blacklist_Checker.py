import geoip2.database
import csv
import os
import sys
import time
from collections import defaultdict
import ipaddress
from ipwhois import IPWhois

# - This script will compare individual IPs from either a CSV file or a python list
# to a second flat-file blocklist containing either individual IPs or
# CIDR subnets, printing results to STDOUT. For blocklists containing CIDR 
# ranges, the script will check if input IPs fall within any listed subnet.
# - Use this script by calling print_parse_csv() or print_parse_list()
# - Input IP addresses will be deduplicated before lookups are performed
# - This script can optionally filter blocklist hit/miss results for a specified ISO2
# country code by passing the 'country_code=' parameter to either print_parse_()
# function
# - This script can optionally expand resulting IP addresses into their registered
# netblocks (performing WHOIS lookups with IPWhois) and list results by country
# provided on registration. This can be toggled independently for blocklist
# hits and misses. To do so, set the boolean 'lookup_hits=' and 'lookup_misses='
# parameters when calling either print_parse_() function. Netblock results will
# be deduplicated, but no attempt is made to determine if they overlap (e.g. are
# subnets/supernets of each other)

PATH_TO_MAXMIND = r'/path/to/maxmind.mmdb'
PATH_TO_BLOCKLIST = r'/path/to/existing/blocklist.txt'

print(f'[{time.strftime("%H:%M:%S")}] Script starting')
GEOIP2_READER = geoip2.database.Reader(PATH_TO_MAXMIND)
print(f'[{time.strftime("%H:%M:%S")}] MaxMind database loaded from {PATH_TO_MAXMIND}')
COUNTER_DICTIONARY = defaultdict(lambda: defaultdict(int))
IP_DICT = {}

def parse_row_one_column(row, ip_column_header):
	this_ip = row[ip_column_header]
	if (this_ip in IP_DICT.keys()):
		this_country = IP_DICT[this_ip]
	else:
		try:
			this_country = GEOIP2_READER.city(this_ip).country.iso_code
		except:
			this_country = 'Unknown'
		IP_DICT[this_ip] = this_country
	COUNTER_DICTIONARY[this_country]['Total_Events'] += 1
	COUNTER_DICTIONARY['Event_Totals']['Total_Events'] += 1

def parse_csv_one_column(input_path, column_header_1,estreamer_formatted=False):
	print(f'[{time.strftime("%H:%M:%S")}] Parsing CSV in single-column mode')
	with open(input_path, mode='r',errors='ignore') as csv_file:
		# read first line of csv file, split by comma, store as list
		firstline = csv_file.readline().replace('"','').split(',')
		# reset file reader position to 0
		csv_file.seek(0)
		# test whether the expected column header is present
		web_export_formatted = (column_header_1 in firstline)
		if web_export_formatted:
			csv_reader = csv.DictReader(csv_file)
			print(f'[{time.strftime("%H:%M:%S")}] Column header found: {column_header_1}')
		else:
			print(f'[{time.strftime("%H:%M:%S")}] Column header not found: {column_header_1}')
			# define headers consistent with LR CSV export
			# WARNING: if using an export mechanism other than LR csv export
			# for this specific report, the columns may be different
			if estreamer_formatted:
				print(f'[{time.strftime("%H:%M:%S")}] Assuming {column_header_1} in column 14 (LR eStreamer report), loading data accordingly')
				csv_field_names = [None,None,None,None,None,None,None,None,None,None,None,None,None,column_header_1,None,None,None,None,None]
			else:
				print(f'[{time.strftime("%H:%M:%S")}] Assuming {column_header_1} in column 12, loading data accordingly')
				csv_field_names = [None,None,None,None,None,None,None,None,None,None,None,None,column_header_1,None,None,None,None]
			csv_reader = csv.DictReader(csv_file, fieldnames=csv_field_names)
		for row in csv_reader:
			parse_row_one_column(row, column_header_1)	
	print(f'[{time.strftime("%H:%M:%S")}] CSV parsing complete')

def check_blocklist(blocklist_path,target_ips):
	blocklist_ips = []
	blocklist_hits = []
	blocklist_misses = []
	
	with open(blocklist_path):
		blocklist_ips = [ipaddress.ip_network(line.rstrip('\n')) for line in open(blocklist_path)]
		print(f'[{time.strftime("%H:%M:%S")}] Blocklist loaded from {blocklist_path}')
	for target_ip in target_ips:
		set_true = False
		for blocklist_ip in blocklist_ips:
			if ipaddress.ip_address(target_ip) in blocklist_ip:
				set_true = True
		if set_true:
			blocklist_hits.append(target_ip)
		else:
			blocklist_misses.append(target_ip)
			
	return blocklist_hits,blocklist_misses
	
def get_registrations(target_list):
	registration_list = []
	for target_ip in target_list:
		registration = IPWhois(target_ip).lookup_rdap()
		if registration['asn_cidr'] not in [x['asn_cidr'] for x in registration_list]:
			registration_list.append(registration)
	[x['asn_cidr'] for x in registration_list]
	registration_list = sorted(registration_list, key=lambda x: x['asn_country_code'])
	# return list of registration objects (dicts)
	return registration_list
	
def print_registrations(registration_list,geolocation_dict):
	# compare a list of registration objects to a dictionary of
	# ip:country mappings (indexed by ip)
	print('Netblock (WHOIS),Country (WHOIS),Country (MaxMind)')
	for record in registration_list:
		if geolocation_dict[record['query']] != record["asn_country_code"]:
			conflict = '     **** MaxMind/WHOIS CONFLICT ****'
		else:
			conflict = ''
		print(f'{record["asn_cidr"]},{record["asn_country_code"]},{geolocation_dict[record["query"]]}{conflict}')
	
def print_parse_csv(csv_path,country_code=None,lookup_hits=False,lookup_misses=True,blocklist_path=PATH_TO_BLOCKLIST,estreamer_formatted=False):
	parse_csv_one_column(csv_path, 'IP Address (Origin)',estreamer_formatted=estreamer_formatted)
	if country_code:
		print(f'[{time.strftime("%H:%M:%S")}] **** Filterting results for country: {country_code} ****')
		ip_list = list({k:v for (k,v) in IP_DICT.items() if v == country_code}.keys())
	else:
		ip_list = list(IP_DICT.keys())
	print(f'[{time.strftime("%H:%M:%S")}] Extracted addresses from CSV:','\n',ip_list)
	hits,misses = check_blocklist(PATH_TO_BLOCKLIST,ip_list)
	print(f'[{time.strftime("%H:%M:%S")}] Blocklist hits for input CSV:','\n',hits)
	if lookup_hits and len(hits):
		print(f'[{time.strftime("%H:%M:%S")}] Retrieving WHOIS netblock information for blocklist hits. This may take some time.')
		hits_lookups = get_registrations(hits)
		print(f'[{time.strftime("%H:%M:%S")}] WHOIS Netblock information for blocklist hits (deduplicated)')
		print_registrations(hits_lookups,IP_DICT)

	print(f'[{time.strftime("%H:%M:%S")}] Blocklist misses for input CSV:','\n',misses)
	if lookup_misses and len(misses):
		print(f'[{time.strftime("%H:%M:%S")}] Retrieving WHOIS netblock information for blocklist misses. This may take some time.')
		misses_lookups = get_registrations(misses)
		print(f'[{time.strftime("%H:%M:%S")}] WHOIS netblock information for blocklist misses (deduplicated):')
		print_registrations(misses_lookups,IP_DICT)
	
def print_parse_list(target_list,country_code=None,lookup_hits=False,lookup_misses=True,blocklist_path=PATH_TO_BLOCKLIST):
	# deduplicate input
	target_list = list(set(target_list))
	print(f'[{time.strftime("%H:%M:%S")}] Checking blocklist for following IPs:','\n',target_list)
	# geolocate input ips
	country_dict = {x:GEOIP2_READER.city(x).country.iso_code for x in target_list}
	if country_code:
		print(f'[{time.strftime("%H:%M:%S")}] **** Filterting results for country: {country_code} ****')
		target_list = list({k:v for (k,v) in country_dict.items() if v == country_code}.keys())
	hits,misses = check_blocklist(blocklist_path,target_list)

	print(f'[{time.strftime("%H:%M:%S")}] Blocklist hits for input list:','\n',hits)
	if lookup_hits and len(hits):
		print(f'[{time.strftime("%H:%M:%S")}] Retrieving WHOIS netblock information for blocklist hits. This may take some time.')
		hits_lookups = get_registrations(hits)
		print(f'[{time.strftime("%H:%M:%S")}] WHOIS netblock information for blocklist hits (deduplicated)')
		print_registrations(hits_lookups,country_dict)

	print(f'[{time.strftime("%H:%M:%S")}] Blocklist misses for input list','\n',misses)
	if lookup_misses and len(misses):
		print(f'[{time.strftime("%H:%M:%S")}] Retrieving WHOIS netblock information for blocklist misses. This may take some time.')
		misses_lookups = get_registrations(misses)
		print(f'[{time.strftime("%H:%M:%S")}] WHOIS netblock information for blocklist misses (deduplicated)')
		print_registrations(misses_lookups,country_dict)
# parse recon event report format (IP in column 12)
# print_parse_csv(r'/path/to/csv.csv',lookup_hits=False,lookup_misses=True,country_code='US')
# parse eStreamer report format:
# print_parse_csv(r'/path/to/csv.csv',lookup_hits=False,lookup_misses=True,country_code='US',estreamer_formatted=True)
#print_parse_list(['8.8.8.8'],lookup_misses=True,lookup_hits=True,country_code=None)