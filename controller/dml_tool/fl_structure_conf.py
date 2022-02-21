import argparse
import json
import os

from conf_utils import read_json, load_node_info


class Conf:
	def __init__ (self, name):
		self.name = name
		self.trainer_fraction = 0
		self.father_node = ''
		self.child_node = []
		self.sync = 0
		self.epoch = 0
		self.connect = {}

	def __hash__ (self):
		return hash (self.name)

	def to_json (self):
		if self.trainer_fraction != 0:
			return {
				'trainer_fraction': self.trainer_fraction,
				'sync': self.sync,
				'child_node': self.child_node,
				'connect': self.connect,
			}
		else:
			return {
				'epoch': self.epoch,
				'father_node': self.father_node,
				'connect': self.connect,
			}


def gen_conf (all_node, conf_json, link_json, output_path):
	node_conf_map = {}
	node_list = conf_json ['node_list']

	# aggregator
	aggregator = node_list [0]
	agg_name = aggregator ['name']
	agg_conf = node_conf_map [agg_name] = Conf (agg_name)
	agg_conf.trainer_fraction = aggregator ['trainer_fraction']
	agg_conf.sync = aggregator ['sync']

	if agg_name in link_json:
		link_list = link_json [agg_name]
		for link in link_list:
			dest = link ['dest']
			assert dest in all_node, Exception ('no such node called ' + dest)
			assert dest not in agg_conf.connect, Exception (
				'duplicate link from ' + agg_name + ' to ' + dest)
			agg_conf.connect [dest] = all_node [dest].ip + ':' + str (all_node [dest].port)

	# trainers
	for i in range (1, len (node_list)):
		trainer = node_list [i]
		name = trainer ['name']
		assert name not in node_conf_map, Exception (
			'duplicate node: ' + name)
		conf = node_conf_map [name] = Conf (name)

		conf.epoch = trainer ['epoch']
		conf.father_node = agg_name
		agg_conf.child_node.append (name)

		if name in link_json:
			link_list = link_json [name]
			for link in link_list:
				dest = link ['dest']
				assert dest in all_node, Exception ('no such node called ' + dest)
				assert dest not in conf.connect, Exception (
					'duplicate link from ' + name + ' to ' + dest)
				conf.connect [dest] = all_node [dest].ip + ':' + str (all_node [dest].port)

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
