import argparse
import json
import os

from conf_utils import read_json, load_node_info


class Conf:
	def __init__ (self, name, ring_size, pos, next_name, sync, epoch):
		self.name = name
		self.ringSize = ring_size
		self.pos = pos
		self.nextName = next_name
		self.sync = sync
		self.epoch = epoch
		self.connect = {}

	def __hash__ (self):
		return hash (self.name)

	def to_json (self):
		return {
			'ring_size': self.ringSize,
			'pos': self.pos,
			'next_name': self.nextName,
			'sync': self.sync,
			'epoch': self.epoch,
			'connect': self.connect
		}


def gen_conf (all_node, conf_json, link_json, output_path):
	node_conf_map = {}
	node_list = conf_json ['node_list']
	next_index = -1

	for i in range (len (node_list)):
		node = node_list [i]
		name = node ['name']
		assert name not in node_conf_map, Exception ('duplicate node: ' + name)
		conf = node_conf_map [name] = Conf (name, len (node_list), i,
			node_list [next_index] ['name'], conf_json ['sync'], node ['epoch'])
		next_index += 1

		if name in link_json:
			link_list = link_json [name]
			for link in link_list:
				dest = link ['dest']
				assert dest in all_node, Exception ('no such node called ' + dest)
				assert dest not in conf.connect, Exception (
					'duplicate link from ' + name + ' to ' + dest)
				conf.connect [dest] = all_node [dest].ip + ':' + str (all_node [dest].port)

	for name in node_conf_map:
		conf_path = os.path.join (output_path, name + '_structure.conf')
		with open (conf_path, 'w') as f:
			f.writelines (json.dumps (node_conf_map [name].to_json (), indent=2))


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
