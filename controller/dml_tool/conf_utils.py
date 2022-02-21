import json
from typing import Dict


class NodeInfo (object):
	def __init__ (self, name: str, ip: str, port: int):
		self.name: str = name
		self.ip: str = ip
		self.port: int = port


def read_json (path: str):
	with open (path, 'r') as f:
		return json.loads (f.read ().replace ('\'', '\"'))


def load_node_info (path: str):
	"""
	return three dicts: emulated node only, physical node only, and all node.
	"""
	node_info_json = read_json (path)

	emulated_node: Dict [str, NodeInfo] = {}
	physical_node: Dict [str, NodeInfo] = {}
	all_node: Dict [str, NodeInfo] = {}

	emulated_node_json = node_info_json ['emulated_node']
	for name, val in emulated_node_json.items ():
		emulated_node [name] = NodeInfo (name, val ['ip'], val ['port'])
		all_node [name] = emulated_node [name]

	physical_node_json = node_info_json ['physical_node']
	for name, val in physical_node_json.items ():
		physical_node [name] = NodeInfo (name, val ['ip'], val ['port'])
		all_node [name] = physical_node [name]

	return emulated_node, physical_node, all_node
