import argparse
import json
import os
from collections import deque

from conf_utils import read_json, load_node_info


class Conf:
	def __init__ (self, name):
		self.name = name
		self.layer = []
		self.father_node = []
		self.child_node = []
		self.child_num = []
		self.curr_child_num = []
		self.sync = []
		self.epoch = 0
		self.connect = {}
		self.forward = {}
		self.n_hop = {}

	def __hash__ (self):
		return hash (self.name)

	def to_json (self):
		return {
			'layer': self.layer [::-1],
			'father_node': self.father_node [::-1],
			'child_node': self.child_node [::-1],
			'sync': self.sync [::-1],
			'epoch': self.epoch,
			'connect': self.connect,
			'forward': self.forward
		}


def gen_conf (all_node, conf_json, link_json, output_path):
	node_conf_map = {}
	father_queue = deque (['top'])
	queue = deque ([])

	for node in conf_json ['node_list']:
		name = node ['name']
		if name not in node_conf_map:
			node_conf_map [name] = Conf (name)
		conf = node_conf_map [name]
		conf.layer.append (node ['layer'])

		# connect to the father node.
		father_name = father_queue.popleft ()
		if father_name == name:
			conf.father_node.append ('self')
		elif father_name == 'top':
			conf.father_node.append ('top')
		else:
			conf.father_node.append (father_name)

		# let the father node connect to it.
		if len (queue) != 0:
			# father node.
			u_e = node_conf_map [queue.popleft ()]
			# at the curr-th child nodes set of father node.
			curr = 0
			while u_e.curr_child_num [curr] == u_e.child_num [curr]:
				curr = curr + 1
			# is the first node of this child nodes set.
			if curr == len (u_e.child_node):
				u_e.child_node.append ([])
			if u_e.name == name:
				u_e.child_node [curr].append ('self')
			else:
				u_e.child_node [curr].append (name)
			u_e.curr_child_num [curr] = u_e.curr_child_num [curr] + 1

		if 'sync' in node:
			conf.sync.append (node ['sync'])
		else:
			conf.sync.append (0)
		if node ['layer'] == 1:
			conf.epoch = node ['epoch']  # only trainer needs epoch.
			conf.child_node.append ([])  # trainer does not have child node.
		else:
			# only aggregator has child node.
			for _ in range (node ['child_num']):
				# let the later [child_num] node be able to call the above
				# {father_queue.popleft ()} part to connect to it.
				father_queue.append (name)
				# let the later [child_num] node be able to call the above
				# {if len (queue) != 0} part to make it connect to the later [child_num] node.
				queue.append (name)
			conf.curr_child_num.append (0)
			conf.child_num.append (node ['child_num'])

	for src in link_json:
		conf = node_conf_map [src]
		conf.n_hop [src] = 0  # to itself.
		link_list = link_json [src]
		for link in link_list:
			dest = link ['dest']
			assert dest in all_node, Exception ('no such node called ' + dest)
			assert dest not in conf.connect, Exception (
				'duplicate link from ' + src + ' to ' + dest)
			conf.connect [dest] = all_node [dest].ip + ':' + str (all_node [dest].port)
			conf.n_hop [dest] = 1

	flag = True
	while flag:
		flag = False
		for i_name in node_conf_map:
			node_i = node_conf_map [i_name]
			hop1 = node_i.n_hop
			for j_name in node_i.connect:
				node_j = node_conf_map [j_name]
				if not i_name in node_j.connect:
					continue
				hop2 = node_j.n_hop
				for dest in hop1:
					if dest not in hop2 or node_j.n_hop [dest] > node_i.n_hop [dest] + 1:
						flag = True
						node_j.forward [dest] = all_node [i_name].ip + ':' + str (all_node [i_name].port)
						node_j.n_hop [dest] = node_i.n_hop [dest] + 1

	for name in node_conf_map:
		file_path = os.path.join (output_path, name + '_structure.conf')
		with open (file_path, 'w') as file:
			file.writelines (json.dumps (node_conf_map [name].to_json (), indent=2))


if __name__ == '__main__':
	dirname = os.path.abspath (os.path.dirname (__file__))
	parser = argparse.ArgumentParser ()
	parser.add_argument ('-s', '--structure', dest='structure', required=True, type=str,
		help='./relative/path/to/structure/json/file')
	parser.add_argument ('-l', '--link', dest='link', required=False, type=str,
		default='../links.json', help='./relative/path/to/link/json/file, default = ../links.json')
	parser.add_argument ('-n', '--node', dest='node', required=False, type=str,
		default='../node_info.json', help='./relative/path/to/node/info/json/file, default = ../node_info.json')
	parser.add_argument ('-o', '--output', dest='output', required=False, type=str,
		default='../dml_file/conf', help='./relative/path/to/output/folder/, default = ../dml_file/conf/')
	args = parser.parse_args ()

	if args.node [0] != '/':
		pathNode = os.path.join (dirname, args.node)
	else:
		pathNode = args.node
	_, _, allNode = load_node_info (pathNode)

	if args.structure [0] != '/':
		pathStructure = os.path.join (dirname, args.structure)
	else:
		pathStructure = args.structure
	confJson = read_json (pathStructure)

	if args.link [0] != '/':
		pathLink = os.path.join (dirname, args.link)
	else:
		pathLink = args.link
	linkJson = read_json (pathLink)

	if args.output [0] != '/':
		pathOutput = os.path.join (dirname, args.output)
	else:
		pathOutput = args.output
	gen_conf (allNode, confJson, linkJson, pathOutput)
