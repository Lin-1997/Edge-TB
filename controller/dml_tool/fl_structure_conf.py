import argparse
import json
import os


def read_json (filename):
	with open (os.path.join (dirname, filename), 'r') as f:
		return json.loads (f.read ().replace ('\'', '\"'))


# we assume that you followed the rules stated in controller/ctl_run_example.py.
# the node name starts with a letter, followed by numbers.
# emulated nodes map port 4444 to host port 8000+x.
# physical nodes listen on port 4444.
def node_to_path (dst_name):
	# from whatever to physical nodes.
	if dst_name in _p_node:
		# this port number should be the same as the one defined in controller/dml_app/el_peer.py.
		return _p_node [dst_name] + ':4444'
	# from whatever to emulated nodes.
	else:
		return node_to_emulator_ip (dst_name) + ':' + str (8000 + int (dst_name [1:]))


def node_to_emulator_ip (_node):
	for name in _emulator:
		if _node in _e_node [name]:
			return _emulator [name]


class Conf:
	def __init__ (self, _name):
		self.name = _name
		self.trainer_fraction = 0
		self.father_node = []
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


def gen_conf ():
	# aggregator
	aggregator = _node_list [0]
	agg_name = aggregator ['name']
	agg_conf = node_conf_map [agg_name] = Conf (agg_name)
	agg_conf.trainer_fraction = aggregator ['trainer_fraction']
	agg_conf.sync = aggregator ['sync']

	if agg_name in link_json:
		link_list = link_json [agg_name]
		for link in link_list:
			dest = link ['dest']
			assert dest not in agg_conf.connect, Exception (
				'duplicate link from ' + agg_name + ' to ' + dest)
			agg_conf.connect [dest] = node_to_path (dest)

	# trainers
	for i in range (1, len (_node_list)):
		trainer = _node_list [i]
		name = trainer ['name']
		assert name not in node_conf_map, Exception (
			'duplicate node: ' + name)
		conf = node_conf_map [name] = Conf (name)

		conf.epoch = trainer ['epoch']
		conf.father_node.append (agg_name)
		agg_conf.child_node.append (name)

		if name in link_json:
			link_list = link_json [name]
			for link in link_list:
				dest = link ['dest']
				assert dest not in conf.connect, Exception (
					'duplicate link from ' + name + ' to ' + dest)
				conf.connect [dest] = node_to_path (dest)

	for name in node_conf_map:
		file_path = os.path.join (dirname, args.output, name + '_structure.conf')
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
		default='../node_ip.json', help='./relative/path/to/node/ip/json/file, default = ../node_ip.json')
	parser.add_argument ('-o', '--output', dest='output', required=False, type=str,
		default='../dml_file/conf', help='./relative/path/to/output/folder/, default = ../dml_file/conf/')
	args = parser.parse_args ()

	node_ip_json = read_json (args.node)
	# Dict [str, str], emulator's name to emulator's ip.
	_emulator = node_ip_json ['emulator']
	# Dict [str, List], emulator's name to emulated node' name in this emulator.
	_e_node = node_ip_json ['emulated_node']
	# Dict [str, str], physical node's name to physical node's ip.
	_p_node = node_ip_json ['physical_node']

	conf_structure_json = read_json (args.structure)
	_node_list = conf_structure_json ['node_list']

	link_json = read_json (args.link)

	node_conf_map = {}

	gen_conf ()
