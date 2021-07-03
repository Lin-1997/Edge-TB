import argparse
import json
import os


def read_json (filename):
	with open (os.path.join (dirname, filename), 'r') as f:
		return json.loads (f.read ().replace ('\'', '\"'))


# we assume that the node name starts with a letter, followed by numbers.
# emulated nodes map port 4444 to host port 8000+x.
# physical nodes listen on port 4444.
def node_to_path (dst_name):
	# from whatever to physical nodes.
	if dst_name in _p_node:
		# this port number should be the same as the one defined in controller/dml_app/gl_peer.py.
		return _p_node [dst_name] + ':4444'
	# from whatever to emulated nodes.
	else:
		return node_to_emulator_ip (dst_name) + ':' + str (8000 + int (dst_name [1:]))


def node_to_emulator_ip (_node):
	for name in _emulator:
		if _node in _e_node [name]:
			return _emulator [name]


class Conf:
	def __init__ (self, _name, _sync, _epoch):
		self.name = _name
		self.sync = _sync
		self.epoch = _epoch
		self.connect = {}

	def __hash__ (self):
		return hash (self.name)

	def to_json (self):
		return {
			'sync': self.sync,
			'epoch': self.epoch,
			'connect': self.connect,
		}


def gen_conf ():
	for node in node_list:
		name = node ['name']
		assert name not in node_conf_map, Exception (
			'duplicate node: ' + name)
		conf = node_conf_map [name] = Conf (name, sync, node ['epoch'])

		if name in links_json:
			link_list = links_json [name]
			for link in link_list:
				dest = link ['dest']
				assert dest not in conf.connect, Exception (
					'duplicate link from ' + name + ' to ' + dest)
				conf.connect [dest] = node_to_path (dest)

	for name in node_conf_map:
		conf_path = os.path.join (dirname, '../dml_file/conf', name + '_structure.conf')
		with open (conf_path, 'w') as f:
			f.writelines (json.dumps (node_conf_map [name].to_json (), indent=2))


if __name__ == '__main__':
	dirname = os.path.abspath (os.path.dirname (__file__))
	parser = argparse.ArgumentParser ()
	parser.add_argument ('-f', '--file', dest='file', required=True, type=str,
		help='./relative/path/to/conf/file')
	args = parser.parse_args ()

	node_ip_json = read_json ('../node_ip.json')
	# Dict [str, str], emulator's name to emulator's ip.
	_emulator = node_ip_json ['emulator']
	# Dict [str, List], emulator's name to emulated node' name in this emulator.
	_e_node = node_ip_json ['emulated_node']
	# Dict [str, str], physical node's name to physical node's ip.
	_p_node = node_ip_json ['physical_node']

	conf_json = read_json (args.file)
	sync = conf_json ['sync']
	node_list = conf_json ['node_list']

	links_json = read_json ('../links.json')

	node_conf_map = {}

	gen_conf ()
