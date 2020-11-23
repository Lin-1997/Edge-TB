import argparse
import json
import os
from collections import deque


class NodeEnv:
	def __init__ (self, _name, _index):
		self.name = _name
		self.type = _type
		self.layer = []
		self.worker_fraction = _worker_fraction
		self.up_node = []
		self.down_node = []
		self.down_num = []
		self.curr_down_num = []
		self.sync = []
		self.epoch = 0
		self.batch_size = _batch_size [_index]
		self.train_start_i = _train_start_i [_index]
		self.train_len = _train_len [_index]
		self.test_start_i = _test_start_i [_index]
		self.test_len = _test_len [_index]
		self.connect = {}
		self.forward = {}
		self.bw = {}
		self.n_hop = {}

	def __hash__ (self):
		return hash (self.name)

	def to_json (self):
		_string = \
			'{\n' \
			+ '"type": ' + str (self.type) + ',\n' \
			+ '"layer": ' + str (self.layer [::-1]) + ',\n' \
			+ '"worker_fraction": ' + str (self.worker_fraction) + ',\n' \
			+ '"up_node": ' + str (self.up_node [::-1]) + ',\n' \
			+ '"down_node": ' + str (self.down_node [::-1]) + ',\n' \
			+ '"sync": ' + str (self.sync [::-1]) + ',\n' \
			+ '"epoch": ' + str (self.epoch) + ',\n' \
			+ '"batch_size": ' + str (self.batch_size) + ',\n' \
			+ '"train_start_i": ' + str (self.train_start_i) + ',\n' \
			+ '"train_len": ' + str (self.train_len) + ',\n' \
			+ '"test_start_i": ' + str (self.test_start_i) + ',\n' \
			+ '"test_len": ' + str (self.test_len) + ',\n' \
			+ '"connect": ' + str (self.connect) + ',\n' \
			+ '"forward": ' + str (self.forward) + '\n' \
			+ '}\n'
		return _string


def node_to_server_ip (_node):
	for name in _server:
		if _node in _container [name]:
			return _server [name]


def hop_between_nodes (_node1, _node2):
	if _node1 in _device or _node2 in _device:
		return 1
	# try to use the container from the same server when need the same hop for forwarding.
	if node_to_server_ip (_node1) == node_to_server_ip (_node2):
		return 0.99
	return 1


def node_to_path (src_name, dst_name):
	# from container to container.
	if src_name not in _device and dst_name not in _device:
		return 'http://' + 's-' + dst_name + ':' + str (8000 + int (dst_name [1:]))
	# from device to container.
	elif src_name in _device and dst_name not in _device:
		d_ip = node_to_server_ip (dst_name)
		return 'http://' + d_ip + ':' + str (30000 + int (dst_name [1:]))
	# from whatever to device.
	else:
		return 'http://' + _device [dst_name] + ':8888'


def read_json (filename):
	file_path = os.path.join (dirname, filename)
	with open (file_path, 'r') as file:
		return json.loads (file.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


def gen_env ():
	for node in _node_list:
		name = node ['name']
		if name not in node_env_map:
			dataset_index = _dataset_order.index (name)
			node_env_map [name] = NodeEnv (name, dataset_index)
		env = node_env_map [name]
		env.layer.append (node ['layer'])

		# connect to the upper node.
		upper_name = upper_queue.popleft ()
		if upper_name == name:
			env.up_node.append ('self')
		elif upper_name == 'top':
			env.up_node.append ('top')
		else:
			env.up_node.append (upper_name)

		# let the upper node connect to it.
		if len (queue) != 0:
			# upper node.
			u_e = node_env_map [queue.popleft ()]
			# at the curr-th down nodes set of upper node.
			curr = 0
			while u_e.curr_down_num [curr] == u_e.down_num [curr]:
				curr = curr + 1
			# is the first node of this down nodes set.
			if curr == len (u_e.down_node):
				u_e.down_node.append ([])
			if u_e.name == name:
				u_e.down_node [curr].append ('self')
			else:
				u_e.down_node [curr].append (name)
			u_e.curr_down_num [curr] = u_e.curr_down_num [curr] + 1

		if node ['layer'] == 1:
			env.sync.append (0)  # trainer does not have sync.
			env.epoch = node ['epoch']  # only trainer needs epoch.
			env.down_node.append ([])  # trainer does not have down node.
		else:
			env.sync.append (node ['sync'])  # only aggregator needs sync.
			# only aggregator has down node.
			for _ in range (node ['down_num']):
				# let the later [down_num] node be able to call the above
				# {upper_queue.popleft ()} part to connect to it.
				upper_queue.append (name)
				# let the later [down_num] node be able to call the above
				# {if len (queue) != 0} part to make it connect to the later [down_num] node.
				queue.append (name)
			env.curr_down_num.append (0)
			env.down_num.append (node ['down_num'])

	# router.
	for i in range (len (_bw_order)):
		i_name = _bw_order [i]
		env = node_env_map [i_name]
		env.n_hop [i_name] = 0
		for j in range (len (_bw_order)):
			if i != j and _bw [i] [j] != 'None':
				j_name = _bw_order [j]
				next_path = node_to_path (i_name, j_name)
				env.connect [j_name] = next_path
				env.n_hop [j_name] = hop_between_nodes (i_name, j_name)
	flag = True
	while flag:
		flag = False
		for i_name in node_env_map:
			node_i = node_env_map [i_name]
			hop1 = node_i.n_hop
			for j_name in node_i.connect:
				node_j = node_env_map [j_name]
				if not i_name in node_j.connect:
					continue
				hop2 = node_j.n_hop
				for dest in hop1:
					hop_num = hop_between_nodes (i_name, j_name)
					if dest not in hop2 or node_j.n_hop [dest] > node_i.n_hop [dest] + hop_num:
						flag = True
						node_j.forward [dest] = node_to_path (j_name, i_name)
						node_j.n_hop [dest] = node_i.n_hop [dest] + hop_num

	for name in node_env_map:
		file_path = os.path.join (dirname, 'env/', name + '.env')
		with open (file_path, 'w') as file:
			file.writelines (node_env_map [name].to_json ())


if __name__ == '__main__':
	dirname = os.path.abspath (os.path.dirname (__file__))
	parser = argparse.ArgumentParser ()
	parser.add_argument ('-t', '--type', dest='type', required=True, type=int,
		help='1 for datasets-only-env, 2 for full-env')
	args = parser.parse_args ()

	if args.type == 1:
		env_datasets_json = read_json ('env_datasets.txt')
		_dataset_order = env_datasets_json ['order']
		_batch_size = env_datasets_json ['batch_size']
		_train_start_i = env_datasets_json ['train_start_i']
		_train_len = env_datasets_json ['train_len']
		_test_start_i = env_datasets_json ['test_start_i']
		_test_len = env_datasets_json ['test_len']

		for d_i in range (len (_dataset_order)):
			env_string = \
				'{\n' \
				+ '"batch_size": ' + str (_batch_size [d_i]) + ',\n' \
				+ '"train_start_i": ' + str (_train_start_i [d_i]) + ',\n' \
				+ '"train_len": ' + str (_train_len [d_i]) + ',\n' \
				+ '"test_start_i": ' + str (_test_start_i [d_i]) + ',\n' \
				+ '"test_len": ' + str (_test_len [d_i]) + '\n' \
				+ '}\n'
			env_path = os.path.join (dirname, 'env_datasets/', _dataset_order [d_i] + '.env')
			with open (env_path, 'w') as f:
				f.writelines (env_string)

	else:
		env_node_ip_json = read_json ('../node_ip.txt')
		_server = env_node_ip_json ['server']
		_container = env_node_ip_json ['container']
		_device = env_node_ip_json ['device']

		env_tree_json = read_json ('env_tree.txt')
		_type = env_tree_json ['type']
		_worker_fraction = env_tree_json ['worker_fraction']
		_node_list = env_tree_json ['node_list']

		env_datasets_json = read_json ('env_datasets.txt')
		_dataset_order = env_datasets_json ['order']
		_batch_size = env_datasets_json ['batch_size']
		_train_start_i = env_datasets_json ['train_start_i']
		_train_len = env_datasets_json ['train_len']
		_test_start_i = env_datasets_json ['test_start_i']
		_test_len = env_datasets_json ['test_len']

		env_bw_json = read_json ('../bw.txt')
		_bw_order = env_bw_json ['order']
		_bw = env_bw_json ['bw']

		node_env_map = {}
		upper_queue = deque (['top'])
		queue = deque ([])
		gen_env ()
