import json
import os
from collections import deque

import numpy as np


class HostEnv:
	def __init__ (self, _id):
		self.id = _id
		self.type = _type
		self.worker_fraction = _worker_fraction
		self.layer_count = 0
		self.layer = []
		self.up_host = []
		self.down_count = []
		self.current_down = []
		self.down_host = []
		self.sync = []

		index = id_to_index (_id)
		self.local_epoch_num = _local_epoch_num [index]
		self.batch_size = _batch_size [index]
		self.train_start_i = _train_start_i [index]
		self.train_len = _train_len [index]
		self.test_start_i = _test_start_i [index]
		self.test_len = _test_len [index]

		self.node = {}
		self.forward = {}
		self.bw = {}
		self.n_hop = {}

	def __hash__ (self):
		return hash (self.id)

	def to_json (self):
		_string = \
			'{\n' \
			+ '"type": ' + str (self.type) + ',\n' \
			+ '"layer_count": ' + str (self.layer_count) + ',\n' \
			+ '"layer": ' + str (self.layer [::-1]) + ',\n' \
			+ '"up_host": ' + str (self.up_host [::-1]) + ',\n' \
			+ '"down_count": ' + str (self.down_count [::-1]) + ',\n' \
			+ '"down_host": ' + str (self.down_host [::-1]) + ',\n' \
			+ '"sync": ' + str (self.sync [::-1]) + ',\n' \
			+ '"local_epoch_num": ' + str (self.local_epoch_num) + ',\n' \
			+ '"batch_size": ' + str (self.batch_size) + ',\n' \
			+ '"train_start_i": ' + str (self.train_start_i) + ',\n' \
			+ '"train_len": ' + str (self.train_len) + ',\n' \
			+ '"test_start_i": ' + str (self.test_start_i) + ',\n' \
			+ '"test_len": ' + str (self.test_len) + ',\n' \
			+ '"worker_fraction": ' + str (self.worker_fraction) + ',\n' \
			+ '"node": ' + str (self.node) + ',\n' \
			+ '"forward": ' + str (self.forward) + '\n' \
			+ '}\n'
		return _string


def id_to_host (_id):
	if _id > 0:
		return 'n' + str (_id)
	return 'r' + str (-_id)


def host_to_id (_host):
	if _host [0] == 'n':
		return int (_host [1:])
	return -int (_host [1:])


def id_to_path (s_id, d_id):
	# both are containers
	if s_id > 0 and d_id > 0:
		return 'http://' + 's-n' + str (d_id) + ':' + str (8000 + d_id)
	# from device to container
	elif d_id > 0 > s_id:
		s_index = 0
		while d_id > _container_number [s_index]:
			s_index = s_index + 1
		return 'http://' + _server_ip [s_index] + ':' + str (30000 + d_id)
	# from whatever to device
	else:
		return 'http://' + _device_ip [id_to_host (d_id)] + ':8888'


def id_to_index (_id):
	if _id > 0:
		return _id + _device_number - 1
	return _id + _device_number


def read_json (filename):
	file_path = os.path.abspath (os.path.join (dirname, filename))
	with open (file_path, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


def gen_env ():
	for host in _host_list:
		if host ['id'] not in host_env_map:
			host_env_map [host ['id']] = HostEnv (host ['id'])
		env = host_env_map [host ['id']]
		env.layer_count = env.layer_count + 1
		env.layer.append (host ['layer'])
		# connect to upper node
		upper_id = upper_queue.popleft ()
		if upper_id == host ['id']:
			env.up_host.append ('self')
		elif upper_id == 0:
			env.up_host.append ('top')
		else:
			env.up_host.append (id_to_host (upper_id))
		env.sync.append (host ['sync'])
		env.down_count.append (host ['dc'])
		env.current_down.append (0)
		# the later a[dc] nodes can connect to it
		for _ in range (host ['dc']):
			upper_queue.append (host ['id'])
		# let the upper node connect to it
		if len (queue) != 0:
			u_e = host_env_map [queue.popleft ()]
			# at the curr-th down nodes set of upper node
			curr = 0
			while u_e.current_down [curr] == u_e.down_count [curr]:
				curr = curr + 1
			if curr == len (u_e.down_host):
				u_e.down_host.append ([])
			if u_e.id == host ['id']:
				u_e.down_host [curr].append ('self')
			else:
				u_e.down_host [curr].append (id_to_host (host ['id']))
			u_e.current_down [curr] = u_e.current_down [curr] + 1
		# let itself can connect to the later a[dc] nodes
		for _ in range (host ['dc']):
			queue.append (host ['id'])
		# no down node
		if host ['dc'] == 0:
			host_env_map [host ['id']].down_host.append ([])

	# router
	for host_id in range (-_device_number, _container_number [-1] + 1):
		if host_id == 0:
			continue
		env = host_env_map [host_id]
		env.n_hop [id_to_host (host_id)] = 0
		for next_id in range (-_device_number, _container_number [-1] + 1):
			if next_id == host_id or next_id == 0:
				continue
			if node_bw [id_to_index (host_id)] [id_to_index (next_id)] != 0:
				next_host = id_to_host (next_id)
				next_path = id_to_path (host_id, next_id)
				env.node [next_host] = next_path
				env.n_hop [next_host] = 1
	flag = True
	while flag:
		flag = False
		for h1 in host_env_map.values ():
			hop1 = h1.n_hop
			for host_name2 in h1.node:
				h2 = host_env_map [host_to_id (host_name2)]
				hop2 = h2.n_hop
				for dest in hop1:
					if dest not in hop2 or h2.n_hop [dest] > h1.n_hop [dest] + 1:
						flag = True
						h2.forward [dest] = id_to_path (h2.id, h1.id)
						h2.n_hop [dest] = h1.n_hop [dest] + 1

	for key in host_env_map:
		file_path = os.path.abspath (os.path.join (dirname, '../env/', id_to_host (key) + '.env'))
		with open (file_path, 'w') as file:
			file.writelines (host_env_map [key].to_json ())


if __name__ == '__main__':
	dirname = os.path.dirname (__file__)
	env_addr_json = read_json ('env_addr.txt')
	_device_number = env_addr_json ['device_number']
	_container_number = env_addr_json ['container_number']
	_server_ip = env_addr_json ['server_ip']
	_device_ip = env_addr_json ['device_ip']

	env_tree_json = read_json ('env_tree.txt')
	_type = env_tree_json ['type']
	_worker_fraction = env_tree_json ['worker_fraction']
	_host_list = env_tree_json ['host_list']
	_local_epoch_num = env_tree_json ['local_epoch_num']

	env_datasets_json = read_json ('env_datasets.txt')
	_batch_size = env_datasets_json ['batch_size']
	_train_start_i = env_datasets_json ['train_start_i']
	_train_len = env_datasets_json ['train_len']
	_test_start_i = env_datasets_json ['test_start_i']
	_test_len = env_datasets_json ['test_len']

	host_env_map = {}
	upper_queue = deque ([0])  # top
	queue = deque ([])
	node_bw = np.loadtxt (os.path.abspath (os.path.join (dirname, 'bw.txt')))
	gen_env ()
