import json
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

		self.round = _round [id_to_index (_id)]
		self.local_epoch_num = _local_epoch_num [id_to_index (_id)]
		self.batch_size = _batch_size [id_to_index (_id)]
		self.learning_rate = _learning_rate [id_to_index (_id)]
		self.start_index = _start_index [id_to_index (_id)]
		self.end_index = _end_index [id_to_index (_id)]
		self.worker_fraction = _worker_fraction [id_to_index (_id)]

		self.node = {}
		self.forward = {}
		self.bw = {}
		self.n_hop = {}

	def __hash__ (self):
		return hash (self.id)

	def to_json (self):
		_string = \
			'{\r\n' \
			+ '"type": ' + str (self.type) + ',\r\n' \
			+ '"layer_count": ' + str (self.layer_count) + ',\r\n' \
			+ '"layer": ' + str (self.layer [::-1]) + ',\r\n' \
			+ '"up_host": ' + str (self.up_host [::-1]) + ',\r\n' \
			+ '"down_count": ' + str (self.down_count [::-1]) + ',\r\n' \
			+ '"down_host": ' + str (self.down_host [::-1]) + ',\r\n' \
			+ '"sync": ' + str (self.sync [::-1]) + ',\r\n' \
			+ '"round": ' + str (self.round) + ',\r\n' \
			+ '"local_epoch_num": ' + str (self.local_epoch_num) + ',\r\n' \
			+ '"batch_size": ' + str (self.batch_size) + ',\r\n' \
			+ '"learning_rate": ' + str (self.learning_rate) + ',\r\n' \
			+ '"start_index": ' + str (self.start_index) + ',\r\n' \
			+ '"end_index": ' + str (self.end_index) + ',\r\n' \
			+ '"worker_fraction": ' + str (self.worker_fraction) + ',\r\n' \
			+ '"node": ' + str (self.node) + ',\r\n' \
			+ '"forward": ' + str (self.forward) + ',\r\n' \
			+ '"bw": ' + str (self.bw) + '\r\n' \
			+ '}\r\n'
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


def gen_host_env ():
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
		file_name = '../node/env/' + id_to_host (key) + '.env'
		with open (file_name, 'w') as file:
			file.writelines (host_env_map [key].to_json ())


def gen_yml ():
	container_start_number = 1
	for dep_index in range (_server_number):
		# dep-的信息
		str_dep = '---\r\n' \
		          + 'apiVersion: apps/v1\r\n' \
		          + 'kind: Deployment\r\n' \
		          + 'metadata:\r\n' \
		          + '  name: d-etree-' + str (dep_index + 1) + '\r\n' \
		          + 'spec:\r\n' \
		          + '  selector:\r\n' \
		          + '    matchLabels:\r\n' \
		          + '      label: l-p-etree-' + str (dep_index + 1) + '\r\n' \
		          + '  template: \r\n' \
		          + '    metadata:\r\n' \
		          + '      labels:\r\n' \
		          + '        label: l-p-etree-' + str (dep_index + 1) + '\r\n' \
		          + '    spec:\r\n' \
		          + '      hostname: p-etree-' + str (dep_index + 1) + '\r\n' \
		          + '      containers:\r\n'
		# dep中每个host container的信息
		container_number = _container_number [dep_index]
		for host_index in range (container_start_number, container_number + 1):
			str_dep = str_dep \
			          + '      - name: n' + str (host_index) + '\r\n' \
			          + '        image: etree-node:v1.0\r\n' \
			          + '        imagePullPolicy: Never\r\n' \
			          + '        ports:\r\n' \
			          + '        - containerPort: ' + str (8000 + host_index) + '\r\n' \
			          + '        command: ["python3", "node.py"]\r\n' \
			          + '        env:\r\n' \
			          + '        - name: NAME\r\n' \
			          + '          value: "n' + str (host_index) + '"\r\n' \
			          + '        - name: PORT\r\n' \
			          + '          value: "' + str (8000 + host_index) + '"\r\n' \
			          + '        volumeMounts:\r\n' \
			          + '        - name: node\r\n' \
			          + '          mountPath: /home/node\r\n'
		# dep中volume的信息
		str_dep = str_dep \
		          + '      volumes:\r\n' \
		          + '      - name: node\r\n' \
		          + '        persistentVolumeClaim:\r\n' \
		          + '          claimName: pvc-node\r\n'
		# svc的信息
		str_dep = str_dep \
		          + '---\r\n' \
		          + 'apiVersion: v1\r\n' \
		          + 'kind: Service\r\n' \
		          + 'metadata:\r\n' \
		          + '  name: s-etree-' + str (dep_index + 1) + '\r\n' \
		          + 'spec:\r\n' \
		          + '  selector:\r\n' \
		          + '    label: l-p-etree-' + str (dep_index + 1) + '\r\n' \
		          + '  type: NodePort\r\n' \
		          + '  ports:\r\n'
		# svc中每个host port的信息
		for host_index in range (container_start_number, container_number + 1):
			str_dep = str_dep \
			          + '  - name: n' + str (host_index) + '\r\n' \
			          + '    port: ' + str (8000 + host_index) + '\r\n' \
			          + '    targetPort: ' + str (8000 + host_index) + '\r\n' \
			          + '    nodePort: ' + str (30000 + host_index) + '\r\n'
		# 写入一个yml文件
		with open ('../k8s-master/dep-' + str (dep_index + 1) + '.yml', 'w')as f:
			f.writelines (str_dep)
			f.close ()
		# 下一个文件用
		container_start_number = container_number + 1

	with open ('../k8s-master/dep.sh', 'w') as f:
		str_dep_sh = '#!/bin/bash\r\n'
		for i in range (_server_number):
			str_dep_sh = str_dep_sh + 'kubectl delete -f dep-' + str (i + 1) + '.yml\r\n'
		for i in range (_server_number):
			str_dep_sh = str_dep_sh + 'kubectl create -f dep-' + str (i + 1) + '.yml\r\n'
		f.writelines (str_dep_sh)
		f.close ()


def read_json (filename):
	_file = open (filename)
	_str = _file.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"')
	_json = json.loads (_str)
	_file.close ()
	return _json


env_json = read_json ('env.txt')
_server_number = env_json ['server_number']
_device_number = env_json ['device_number']
_server_ip = env_json ['server_ip']
_device_ip = env_json ['device_ip']
_container_number = env_json ['container_number']
_host_list = env_json ['host_list']
_round = env_json ['round']
_local_epoch_num = env_json ['local_epoch_num']
_batch_size = env_json ['batch_size']
_learning_rate = env_json ['learning_rate']
_start_index = env_json ['start_index']
_end_index = env_json ['end_index']
_worker_fraction = env_json ['worker_fraction']

host_env_map = {}
upper_queue = deque ([0])  # 代表"top"
queue = deque ([])

node_bw = np.loadtxt ('bw.txt')

gen_host_env ()
gen_yml ()
