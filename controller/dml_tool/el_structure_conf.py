import argparse
import json
import os
from collections import deque


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


def hop_between_nodes (_node1, _node2):
	if _node1 in _p_node or _node2 in _p_node:
		return 1
	# try to use the emulated node from the same emulator when need the same hop for forwarding.
	if node_to_emulator_ip (_node1) == node_to_emulator_ip (_node2):
		return 0.99
	return 1


class Conf:
	def __init__ (self, _name):
		self.name = _name
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


# Generate structure conf for each node according to the above rules.
def gen_conf ():
	for node in _node_list:
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

	for src in links_json:
		conf = node_conf_map [src]
		conf.n_hop [src] = 0  # to itself.
		link_list = links_json [src]
		for link in link_list:
			dest = link ['dest']
			assert dest not in conf.connect, Exception (
				'duplicate link from ' + src + ' to ' + dest)
			conf.connect [dest] = node_to_path (dest)
			conf.n_hop [dest] = hop_between_nodes (src, dest)

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
					hop_num = hop_between_nodes (i_name, j_name)
					if dest not in hop2 or node_j.n_hop [dest] > node_i.n_hop [dest] + hop_num:
						flag = True
						node_j.forward [dest] = node_to_path (i_name)
						node_j.n_hop [dest] = node_i.n_hop [dest] + hop_num

	for name in node_conf_map:
		file_path = os.path.join (dirname, '../dml_file/conf', name + '_structure.conf')
		with open (file_path, 'w') as file:
			file.writelines (json.dumps (node_conf_map [name].to_json (), indent=2))


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

	conf_structure_json = read_json (args.file)
	_node_list = conf_structure_json ['node_list']

	links_json = read_json ('../links.json')

	node_conf_map = {}
	father_queue = deque (['top'])
	queue = deque ([])

	gen_conf ()
