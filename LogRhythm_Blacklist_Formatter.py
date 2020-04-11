# this script will check a mixed list of IP addresses and CIDR blocks, then break
# that list out into separate lists of IP addresses and ranges (formatted for LogRhyhtm
# 'ip address range' lists), to be used with the LogRhythm autoimport feature

import ipaddress

def parse_blocklist(blocklist_path):
	addresses = []
	ranges = []
	blocklist_ips = []
	with open(blocklist_path):
		blocklist_ips = [line.rstrip('\n') for line in open(blocklist_path)]
	for address in blocklist_ips:
		if "/" in address:
			range = ipaddress.ip_network(address)
			string = f'{str(range.network_address)}~{str(range.broadcast_address)}'
			ranges.append(string)
		else:
			addresses.append(address)
	return addresses,ranges
	
def write_file(input_list, destination_file):
	with open(destination_file, 'w') as file:
		for address in input_list[:(len(input_list)-1)]:
			file.write(f'{address}\n')
		file.write(input_list[len(input_list)-1])

addresses,ranges = parse_blocklist(r'/path/to/combined/blocklist.txt')
write_file(addresses,'LR_Addresses_SOC_IP_Blacklist.txt')
write_file(ranges,'LR_Ranges_SOC_IP_Blacklist.txt')