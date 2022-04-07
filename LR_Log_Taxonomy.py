import networkx
import os
import pathlib
import csv
import re
from anytree import Node, RenderTree
from anytree.render import AsciiStyle

inputPath = r'/home/s3p1a/06_09_2021-LogRhythm_WebLogsExport.csv'
inputString = inputPath
graph_title = re.sub('[( )]','',''.join(inputString.split('/')[-1].split('.')[:-1]))
logSourceNetworks = {}

# to do:
#	add file input argparse
# 	consider changing to defaultdict for efficiency? may need to convert defaultdict to networkx

with open(inputPath,'r') as inputFile:
	inputDict = csv.DictReader(inputFile)
	for asset in inputDict:
		if not asset['Log Source Type'] in logSourceNetworks.keys():
			# use a digraph per https://stackoverflow.com/questions/11479624/is-there-a-way-to-guarantee-hierarchical-output-from-networkx
			logSourceNetworks[asset['Log Source Type']] = networkx.DiGraph()
			
		thisLogSourceNetwork = logSourceNetworks[asset['Log Source Type']]
		# pre-calculate here to avoid confusion when nesting f-strings
		thisLogSourceTypeNodeString = f"[LST] {asset['Log Source Type']}"
		thisClassificationNodeString = f"[CLS] {asset['Classification']}"
		thisCommonEventNodeString = f"[CE] {asset['Common Event']}"
		thisMPERuleNameNodeString = f"[MPE] {asset['MPE Rule Name']}"
		
		# log source type
		if thisLogSourceTypeNodeString in thisLogSourceNetwork:
			thisNode = thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]
			thisNode['counter'] += 1
			thisNode['percentage'] = round(thisNode['counter'] / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]['counter']*100,2)
			thisNode['label'] = f'{thisLogSourceTypeNodeString}: {thisNode["counter"]} ({thisNode["percentage"]}%)'
		else:
			thisLogSourceNetwork.add_node(
				thisLogSourceTypeNodeString,
				counter = 1,
				# bootstrap this valaue with a constant since this is the top level in the taxonomy
				percentage = 0,
				nodeType='Log Source Type',
				label = f'{thisLogSourceTypeNodeString}: 1 ({0}%)'
			)

		# classification
		if thisClassificationNodeString in thisLogSourceNetwork:
			thisNode = thisLogSourceNetwork.nodes[thisClassificationNodeString]
			thisNode['counter'] += 1
			thisNode['percentage'] = round(thisNode['counter'] / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]['counter']*100,2)
			thisNode['label'] = f'{thisClassificationNodeString}: {thisNode["counter"]} ({thisNode["percentage"]}%)'
		else:
			thisLogSourceNetwork.add_node(
				thisClassificationNodeString,
				counter = 1,
				percentage = round(1 / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]['counter']*100,2),
				nodeType='Classification',
				label = f'{thisClassificationNodeString}: 1 ({round(1 / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]["counter"]*100,2)}%)'
			)

		# common event
		if thisCommonEventNodeString in thisLogSourceNetwork:
			thisNode = thisLogSourceNetwork.nodes[thisCommonEventNodeString]
			thisNode['counter'] += 1
			thisNode['percentage'] = round(thisNode['counter'] / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]['counter']*100,2)
			thisNode['label'] = f'{thisCommonEventNodeString}: {thisNode["counter"]} ({thisNode["percentage"]}%)'
		else:
			thisLogSourceNetwork.add_node(
				thisCommonEventNodeString,
				counter = 1,
				percentage = round(1 / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]['counter']*100,2),
				nodeType='Common Event',
				label = f'{thisCommonEventNodeString}: 1 ({round(1 / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]["counter"]*100,2)}%)'
			)

		# mpe rule name	
		if thisMPERuleNameNodeString in thisLogSourceNetwork:	
			thisNode = thisLogSourceNetwork.nodes[thisMPERuleNameNodeString]
			thisNode['counter'] += 1
			thisNode['percentage'] = round(thisNode['counter'] / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]["counter"]*100,2)
			thisNode['label'] = f'{thisMPERuleNameNodeString}: {thisNode["counter"]} ({thisNode["percentage"]}%)'
		else:
			thisLogSourceNetwork.add_node(
				thisMPERuleNameNodeString,
				counter = 1,
				percentage = round(1 / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]['counter']*100,2),
				nodeType='MPE Rule Name',
				label = f'{thisMPERuleNameNodeString}: 1 ({round(1 / thisLogSourceNetwork.nodes[thisLogSourceTypeNodeString]["counter"]*100,2)}%)'
			)
			
		thisLogSourceNetwork.add_edge(thisLogSourceTypeNodeString,thisClassificationNodeString)
		thisLogSourceNetwork.add_edge(thisClassificationNodeString,thisCommonEventNodeString)
		thisLogSourceNetwork.add_edge(thisCommonEventNodeString,thisMPERuleNameNodeString)


def networkxToAnytree(inputNetworkx):
		
	# https://stackoverflow.com/questions/4122390/getting-the-root-head-of-a-digraph-in-networkx-python
	inputNetworkxRootNode = next(networkx.topological_sort(inputNetworkx))
	
	for networkxNodeName,data in inputNetworkx.nodes(data=True):
		data['anyTreeNode'] = Node(data['label'])

	for networkxParent,networkxChild in inputNetworkx.edges():
		inputNetworkx.nodes[networkxChild]['anyTreeNode'].parent = inputNetworkx.nodes[networkxParent]['anyTreeNode']

	return inputNetworkx.nodes[inputNetworkxRootNode]['anyTreeNode']

def printAnyTreeAscii(inputAnyTree):
	for pre, fill, node in RenderTree(inputAnyTree, style=AsciiStyle()):
		print("%s%s" % (pre, node.name))	

testNetwork = logSourceNetworks[next(iter(logSourceNetworks))]
printAnyTreeAscii(networkxToAnytree(testNetwork))
