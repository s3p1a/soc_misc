# this script is used to parse LogRhythm reports and generate aggregate data grouped by
# source country (using a local maxmind database). in its current form, it needs to be customized
# (in the parse_csv_* methods) so that the column headers line up with the target csv file
# (generated either fom the LogRhythm web console, or a specific report from the thick
# client).
# this can output total events per country as a CSV, optionally broken out by event type,
# as well as a geographic heatmap generated with geopandas.

# [setup]
# install conda package manager from https://www.anaconda.com/distribution/
# open conda prompt from start menu, then 'conda install -c conda-forge geopandas'
# download map shapes from https://www.naturalearthdata.com/downloads/110m-cultural-vectors/
# alternate map shapes, with proper ISO2 coding: https://thematicmapping.org/downloads/world_borders.php
# pip install geoip2
# download GeoLite2 City Database from https://dev.maxmind.com/geoip/geoip2/geolite2/, adjust reader path below
# [refs]
# https://towardsdatascience.com/a-complete-guide-to-an-interactive-geographical-map-using-python-f4c5197e23e0
# https://towardsdatascience.com/lets-make-a-map-using-geopandas-pandas-and-matplotlib-to-make-a-chloropleth-map-dddc31c1983d

import geopandas as gpd
import pandas as pd
import geoip2.database
import csv
import os
import sys
import time
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as colors
# import pprint
from collections import defaultdict
import copy

print(f'[{time.strftime("%H:%M:%S")}] Script starting')
reader = geoip2.database.Reader(r'/path/to/maxmind/database.mmdb')
#input_path = r'/default/input/path.csv' # deprecated
shapefile = r'/path/to/naturalearth/shapefile.shp'

counter_dictionary = defaultdict(lambda: defaultdict(int))
ip_dict = {}

def parse_row_two_columns(row, ip_column_header, event_column_header):
	this_ip = row[ip_column_header]
	if (this_ip in ip_dict.keys()):
		this_country = ip_dict[this_ip]
	else:
		try:
			this_country = reader.city(this_ip).country.iso_code
		except:
			this_country = 'Unknown'
		ip_dict[this_ip] = this_country
	this_event = row[event_column_header]
	counter_dictionary[this_country][this_event] += 1
	counter_dictionary[this_country]['Total_Events'] += 1
	counter_dictionary['Event_Totals'][this_event] += 1
	counter_dictionary['Event_Totals']['Total_Events'] += 1

def parse_row_one_column(row, ip_column_header):
	this_ip = row[ip_column_header]
	if (this_ip in ip_dict.keys()):
		this_country = ip_dict[this_ip]
	else:
		try:
			this_country = reader.city(this_ip).country.iso_code
		except:
			this_country = 'Unknown'
		ip_dict[this_ip] = this_country
	counter_dictionary[this_country]['Total_Events'] += 1
	counter_dictionary['Event_Totals']['Total_Events'] += 1
	
def parse_csv_two_columns(input_path, column_header_1, column_header_2):
	
	print(f'[{time.strftime("%H:%M:%S")}] Parsing CSV in two-column mode')
	with open(input_path, mode='r') as csv_file:
		# read first line of csv file, split by comma, store as list
		firstline = csv_file.readline().replace('"','').split(',')
		# reset file reader position to 0
		csv_file.seek(0)
		# test whether the expected column header is present
		web_export_formatted = ((column_header_1 in firstline) and (column_header_2 in firstline))
		if web_export_formatted:
			csv_reader = csv.DictReader(csv_file)
			print(f'[{time.strftime("%H:%M:%S")}] Column headers found: {column_header_1} and {column_header_2}')
		else:
			print(f'[{time.strftime("%H:%M:%S")}] Column headers not found: {column_header_1} and {column_header_2}')
			print(f'[{time.strftime("%H:%M:%S")}] Assuming {column_header_1} in column 13, loading data accordingly')
			print(f'[{time.strftime("%H:%M:%S")}] Assuming {column_header_2} in column 15, loading data accordingly')
			# define headers consistent with LR CSV export
			# WARNING: if using an export mechanism other than LR csv export
			# for this specific report, the columns may be different
			csv_field_names = [None,None,None,None,None,None,None,None,None,None,None,None,None,column_header_1,None,column_header_2,None,None,None]
			csv_reader = csv.DictReader(csv_file, fieldnames=csv_field_names)
		for row in csv_reader:
			parse_row_two_columns(row, column_header_1, column_header_2)
		print(f'[{time.strftime("%H:%M:%S")}] CSV parsing complete')

def parse_csv_one_column(input_path, column_header_1):
	print(f'[{time.strftime("%H:%M:%S")}] Parsing CSV in single-column mode')
	with open(input_path, mode='r') as csv_file:
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
			print(f'[{time.strftime("%H:%M:%S")}] Assuming {column_header_1} in column 12, loading data accordingly')
			# define headers consistent with LR CSV export
			# WARNING: if using an export mechanism other than LR csv export
			# for this specific report, the columns may be different
			csv_field_names = [None,None,None,None,None,None,None,None,None,None,None,None,column_header_1,None,None,None,None]
			csv_reader = csv.DictReader(csv_file, fieldnames=csv_field_names)
		for row in csv_reader:
			parse_row_one_column(row, column_header_1)	
	print(f'[{time.strftime("%H:%M:%S")}] CSV parsing complete')
			
def flatten_dictionary(dictionary):
	flattened_list = []
	for top_level_key in counter_dictionary.keys():
		this_list = []
		this_list.append(top_level_key)
		for common_event in counter_dictionary['Event_Totals']:
			this_list.append(counter_dictionary[top_level_key][common_event])
		flattened_list.append(this_list)
	return flattened_list

# https://stackoverflow.com/questions/18926031/how-to-extract-a-subset-of-a-colormap-as-a-new-colormap-in-matplotlib
def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=32):
    new_cmap = colors.LinearSegmentedColormap.from_list(
        'trunc({n},{a:.2f},{b:.2f})'.format(n=cmap.name, a=minval, b=maxval),
        cmap(np.linspace(minval, maxval, n)))
    return new_cmap

def generate_map(input_dataframe, variable_to_count, event_title = 'Events by Source Country'):
	# generate a new object to prevent changes to variable in caller
	input_dataframe = input_dataframe.copy()
	print(f'[{time.strftime("%H:%M:%S")}] Generating map with aggregation by {variable_to_count}')
	# read shapefile using Geopandas
	map_df = gpd.read_file(shapefile)[['ISO2','geometry']]
	# drop antactica
	map_df.drop((map_df[map_df['ISO2'] == 'AQ'].index), inplace = True)
	index_of_event_totals = input_dataframe[input_dataframe['ISO2'] == 'Event_Totals'].index[0]
	sumEvents = input_dataframe.at[index_of_event_totals,variable_to_count]
	# input_dataframe.sort_values(by=[variable_to_count], inplace = True, ascending = False)
	event_max = input_dataframe[variable_to_count].max()
	
	# merge datasets
	merged_df = pd.merge(map_df, input_dataframe, on = 'ISO2',how = 'left')
	# print(merged_df)
	# choose variable to plot
	variable = variable_to_count
	
	# set the range for the chloropleth
	vmin, vmax = 1, event_max
	
	# create figure and axes for matplotlib
	fig, ax = plt.subplots(1, figsize=(32, 24))
	
	# remove the axis
	ax.axis('off')
	
	palette = truncate_colormap(plt.cm.get_cmap('YlOrRd'), 0.35, 1.0)
	# pprint.pprint(palette._segmentdata)
	for key in ['red','green','blue']:
		newDict = {}
		newList = []
		for value in palette._segmentdata[key]:
			newTuple = (value[0]**2, value[1], value[2])
	#       newTuple = (np.sqrt(value[0]), value[1], value[2])
			newList.append(newTuple)
		newDict[key] = newList
		palette._segmentdata.update(newDict)
		
	# pprint.pprint(palette._segmentdata)
	palette.set_under(color = 'gray')
	
	# Create colorbar as a legend
	sm = plt.cm.ScalarMappable(cmap=palette, norm=plt.Normalize(vmin=vmin, vmax=vmax))
	
	# empty array for the data range
	sm._A = []
	# add the colorbar to the figure
	cbar = fig.colorbar(sm, orientation = 'vertical', shrink = 0.4)
	
	# add a title
	map_title = event_title
	ax.set_title(map_title, fontdict={'fontsize': '25', 'fontweight' : '3'})
	
	totalEvents = f'Total events: {sumEvents}'
	ax.annotate(totalEvents,xy=(0.4, .35),  xycoords='figure fraction', horizontalalignment='left', verticalalignment='top', fontsize=18, color='#555555')
	
	# create map
	merged_df.plot(column=variable, cmap=palette, linewidth=0.2, ax=ax, edgecolor='0.8',vmin=1)
	
	fig.savefig(f'{map_title}.png', dpi=fig.dpi)
	print(f'[{time.strftime("%H:%M:%S")}] Map exported as {map_title}.png')

# def top_five_counts(dict):
# 	# deprecated - this is now handled automatically in prepare_dataframe
# 	iso2_counts = {}
#	for key in dict.keys():
#		iso2_counts[key] = dict[key]['Total_Events']
#	# remove 'Event Totals' row
#	iso2_counts.pop('Event_Totals', None)
#	top_five_iso2 = [x[0] for x in sorted(iso2_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
#	# since we're not using a new dict here, Event Totals will be present in the list. Start index
#	# at 1 to step over it.
#	top_five_events = [x[0] for x in sorted(dict['Event_Totals'].items(), key=lambda x: x[1], reverse=True)[1:6]]
#	top_5_array = []
#	for iso2 in top_five_iso2:
#		for event in top_five_events:
#			top_5_array.append([iso2, event, dict[iso2][event]])
#	return pd.DataFrame(top_5_array)

def prepare_dataframe(input_dict):
	# generate dataframe columns dynamically from observed common events
	dataframe_columns = ['ISO2'] + list(input_dict['Event_Totals'].keys())
	# generate dataframe using observed columns
	output_df = pd.DataFrame(flatten_dictionary(input_dict), columns=dataframe_columns)
	# drop dataframes with invalid ISO2 values
	# null values don't work with == comparisons, so use notnull
	# https://stackoverflow.com/questions/18172851/deleting-dataframe-row-in-pandas-based-on-column-value
	output_df = output_df[output_df['ISO2'].notnull()]
	output_df.drop((output_df[output_df['ISO2'] == 'Unknown'].index), inplace=True)
	# sort dataframe rows by values in Total_Events column
	output_df.sort_values(by=['Total_Events'], inplace=True, ascending=False)
	# order dataframe columns by value in Event_Totals row
	column_order = ['ISO2'] + [x[0] for x in sorted(input_dict['Event_Totals'].items(), key=lambda x: x[1], reverse=True)]
	output_df = output_df[column_order]
	return output_df

def generate_topx(input_dataframe, top_rows=5, top_columns=4, drop_totals=True):
	# generate a new object to prevent changes to variable in caller
	# assumes rows and columns are already sorted, which should take place in prepare_dataframe()
	output_df = input_dataframe.copy()
	if (drop_totals):
		output_df.drop((output_df[output_df['ISO2'] == 'Event_Totals'].index), inplace=True)
		output_df.drop(columns='Total_Events', inplace=True)
	if (top_columns < len(list(output_df))):
		drop_columns = list(output_df)[(top_columns+1):]
		output_df.drop(columns=drop_columns, inplace=True)
	# output_df = output_df[:top_rows]
	output_df = output_df.head(top_rows)
	return output_df
	
def collapse_dataframe(input_dataframe, top_header='ISO2'):
	# Collapses all columns to rows, with the exception of the column specified in top_header
	# Preserves sort order. Useful to format excel charts such as sunburst or tree.
	columns_list = list(input_dataframe)
	columns_list.remove(top_header)
	collapsed_array = []
	for row in input_dataframe[top_header]:
		index_of_row = input_dataframe[input_dataframe['ISO2'] == row].index[0]
		for column in columns_list:
			collapsed_array.append([row,column,input_dataframe.at[index_of_row,column]])
	output_df = pd.DataFrame(collapsed_array, columns=['ISO2','Event','Count'])
	return output_df
	
def parseIntrusionEvents(input_path,date_string=time.strftime("%Y%m%d-%H%M%S")):
	# Example: Parse intrusion events report
	# input_path = r'/override/input/path.csv'
	#parse csv file, performing geoip lookups and performing counts inline
	parse_csv_two_columns(input_path, 'IP Address (Origin)', 'Common Event')
	results_df = prepare_dataframe(counter_dictionary)
	title_string = f'Intrusion Events by Source Country, {date_string}'
	#generate_map(results_df, 'Total_Events', event_title=title_string)
	results_df.to_csv(f'{title_string}.csv', index = False)
	# export a csv file of top 4 common events across top 5 attackers
	# collapse_dataframe(generate_topx(results_df)).to_csv('Collapsed TopX.csv', index=False)

def parseReconEvents(input_path,input_path_two=None,date_string=time.strftime("%Y%m%d-%H%M%S")):
	# Example: Parse recon/scanning events report
	# input_path = r'/override/input/path.csv'
	# parse csv file, performing geoip lookups and performing counts inline
	parse_csv_one_column(input_path, 'IP Address (Origin)')
	if input_path_two:
		print(f'[{time.strftime("%H:%M:%S")}] Second CSV file found')
		parse_csv_one_column(input_path_two, 'IP Address (Origin)')
	results_df = prepare_dataframe(counter_dictionary)
	title_string = f'Aggressive Recon Events by Source Country, {date_string}'
	#generate_map(results_df, 'Total_Events', event_title=title_string)
	results_df.to_csv(f'{title_string}.csv', index = False)
	# shim in quick print for a country of interest:
	#print(f"USA Hits: {counter_dictionary['US']['Total_Events']}")
	#ip_list = list({k:v for (k,v) in ip_dict.items() if v == "US"}.keys())
	#print(f"USA IPs: {ip_list}")
	
	# collapse_dataframe(generate_topx(results_df,drop_totals=False)).to_csv('Collapsed TopX.csv', index=False)
	
# intrusion events
parseIntrusionEvents(r'/path/to/csv.csv',date_string='January 1970')

# recon events, one file, with custom date string
# parseReconEvents(r'/path/to/csv.csv',date_string='Recon January 1970')
# recon events, two files with custom date string
# parseReconEvents(r'/path/to/csv1.csv',r'/path/to/csv2.csv',date_string='January 1970')
