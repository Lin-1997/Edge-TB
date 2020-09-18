import json
import os
from collections import deque

import numpy as np


class HostEnv:
	def __init__ (self, _id, _type=0):
		self.id = _id
		self.type = _type
		self.layer_count = 0
		self.layer = []
		self.up_host = []
		self.down_count = []
		self.current_down = []
		self.down_host = []
		self.sync = []

		index = id_to_index (_id)
		self.round = _round [index]
		self.local_epoch_num = _local_epoch_num [index]
		self.batch_size = _batch_size [index]
		self.learning_rate = _learning_rate [index]
		self.start_index = _start_index [index]
		self.end_index = _end_index [index]
		self.worker_fraction = _worker_fraction [index]

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
			+ '"round": ' + str (self.round) + ',\n' \
			+ '"local_epoch_num": ' + str (self.local_epoch_num) + ',\n' \
			+ '"batch_size": ' + str (self.batch_size) + ',\n' \
			+ '"learning_rate": ' + str (self.learning_rate) + ',\n' \
			+ '"start_index": ' + str (self.start_index) + ',\n' \
			+ '"end_index": ' + str (self.end_index) + ',\n' \
			+ '"worker_fraction": ' + str (self.worker_fraction) + ',\n' \
			+ '"node": ' + str (self.node) + ',\n' \
			+ '"forward": ' + str (self.forward) + ',\n' \
			+ '"bw": ' + str (self.bw) + '\n' \
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
	# 都是容器
	if s_id > 0 and d_id > 0:
		s_index = 0
		while d_id > _container_number [s_index]:
			s_index = s_index + 1
		return 'http://' + 's-etree-' + str (s_index + 1) + ':' + str (8000 + d_id)
	# return 'http://' + 'n' + str (d_id) + ':' + str (8000 + d_id)
	# 设备发给容器
	elif d_id > 0 > s_id:
		s_index = 0
		while d_id > _container_number [s_index]:
			s_index = s_index + 1
		return 'http://' + _server_ip [s_index] + ':' + str (30000 + d_id)
	# 发给设备
	else:
		return 'http://' + _device_ip [id_to_host (d_id)] + ':8888'


def id_to_index (_id):
	if _id > 0:
		return _id + _device_number - 1
	return _id + _device_number


def gen_env ():
	for host in _host_list:
		# 初始化一个env对象
		if host ['id'] not in host_env_map:
			host_env_map [host ['id']] = HostEnv (host ['id'])
		# 赋值
		env = host_env_map [host ['id']]
		env.layer_count = env.layer_count + 1
		env.layer.append (host ['layer'])
		# 连上父节点
		upper_id = upper_queue.popleft ()
		if upper_id == host ['id']:
			env.up_host.append ('self')
		elif upper_id == 0:
			env.up_host.append ('top')
		else:
			env.up_host.append (id_to_host (upper_id))
		# 占位
		env.sync.append (host ['sync'])
		env.down_count.append (host ['dc'])
		env.current_down.append (0)
		# 是后面a[dc]个的父节点
		for _ in range (host ['dc']):
			upper_queue.append (host ['id'])
		# 让父节点连上自己
		if len (queue) != 0:
			u_e = host_env_map [queue.popleft ()]
			# 在父节点的第curr个子节点集合
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
		# 是后面a[dc]个的父节点
		for _ in range (host ['dc']):
			queue.append (host ['id'])
		# 无子节点占位
		if host ['dc'] == 0:
			host_env_map [host ['id']].down_host.append ([])

	# 路由信息
	for host_id in range (-_device_number, _container_number [-1] + 1):
		if host_id == 0:
			continue
		env = host_env_map [host_id]
		# 到自己0跳
		env.n_hop [id_to_host (host_id)] = 0
		for next_id in range (-_device_number, _container_number [-1] + 1):
			if next_id == host_id or next_id == 0:
				continue
			bw = node_bw [id_to_index (host_id)] [id_to_index (next_id)]
			if bw != 0:
				next_host = id_to_host (next_id)
				next_path = id_to_path (host_id, next_id)
				env.node [next_host] = next_path
				# 到邻居带宽
				env.bw [next_path] = bw
				# 到邻居1跳
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


def read_json (filename):
	file_path = os.path.abspath (os.path.join (dirname, filename))
	with open (file_path, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


dirname = os.path.dirname (__file__)
env_addr_json = read_json ('env_addr.txt')
_device_number = env_addr_json ['device_number']
_container_number = env_addr_json ['container_number']
_server_ip = env_addr_json ['server_ip']
_device_ip = env_addr_json ['device_ip']

env_tree_json = read_json ('env_tree.txt')
_host_list = env_tree_json ['host_list']
_round = env_tree_json ['round']
_local_epoch_num = env_tree_json ['local_epoch_num']
_worker_fraction = env_tree_json ['worker_fraction']

env_datasets_json = read_json ('env_datasets.txt')
_batch_size = env_datasets_json ['batch_size']
_learning_rate = env_datasets_json ['learning_rate']
_start_index = env_datasets_json ['start_index']
_end_index = env_datasets_json ['end_index']

host_env_map = {}
upper_queue = deque ([0])  # 代表"top"
queue = deque ([])
node_bw = np.loadtxt (os.path.abspath (os.path.join (dirname, 'bw.txt')))
gen_env ()
