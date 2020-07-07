import json
from collections import deque

import numpy as np


class Env:
	def __init__ (self, _id, _type=0):
		self.id = _id
		self.type = _type
		self.layer_count = 0
		self.layer = []
		self.up_addr = []
		self.up_bw = []
		self.down_count = []
		self.current_down = []
		self.down_addr = []
		self.down_bw = []
		self.sync = []

		self.round = _round [_id - 1]
		self.local_epoch_num = _local_epoch_num [_id - 1]
		self.batch_size = _batch_size [_id - 1]
		self.learning_rate = _learning_rate [_id - 1]
		self.start_index = _start_index [_id - 1]
		self.end_index = _end_index [_id - 1]
		self.worker_fraction = _worker_fraction [_id - 1]

	def __hash__ (self):
		return hash (self.id)

	def to_json (self):
		_string = \
			'{\r\n' \
			+ '"type": ' + str (self.type) + ',\r\n' \
			+ '"layer_count": ' + str (self.layer_count) + ',\r\n' \
			+ '"layer": ' + str (self.layer [::-1]) + ',\r\n' \
			+ '"up_addr": ' + str (self.up_addr [::-1]) + ',\r\n' \
			+ '"up_bw": ' + str (self.up_bw [::-1]) + ',\r\n' \
			+ '"down_count": ' + str (self.down_count [::-1]) + ',\r\n' \
			+ '"down_addr": ' + str (self.down_addr [::-1]) + ',\r\n' \
			+ '"down_bw": ' + str (self.down_bw [::-1]) + ',\r\n' \
			+ '"sync": ' + str (self.sync [::-1]) + ',\r\n' \
			+ '"round": ' + str (self.round) + ',\r\n' \
			+ '"local_epoch_num": ' + str (self.local_epoch_num) + ',\r\n' \
			+ '"batch_size": ' + str (self.batch_size) + ',\r\n' \
			+ '"learning_rate": ' + str (self.learning_rate) + ',\r\n' \
			+ '"start_index": ' + str (self.start_index) + ',\r\n' \
			+ '"end_index": ' + str (self.end_index) + ',\r\n' \
			+ '"worker_fraction": ' + str (self.worker_fraction) + '\r\n' \
			+ '}\r\n'
		return _string


def format_addr (_id, host, host_list):
	if host == 'n':  # Docker-compose
		return 'http://' + host + str (_id) + ':8888'
	s_index = 0  # K8s
	while _id > host_list [s_index]:
		s_index = s_index + 1
	return 'http://' + host + str (s_index + 1) + ':' + str (8000 + _id)


def gen_env ():
	for a in _list:
		# 初始化一个env对象
		if a ['id'] not in env_map:
			env_map [a ['id']] = Env (a ['id'])
		# 赋值
		env = env_map [a ['id']]
		env.layer_count = env.layer_count + 1
		env.layer.append (a ['layer'])
		# 连上父节点
		upper_id = upper_queue.popleft ()
		if upper_id == a ['id']:
			env.up_addr.append ('self')
			env.up_bw.append (0)  # 用不上
		elif upper_id == 'top':
			env.up_addr.append ('top')
			env.up_bw.append (0)
		else:
			env.up_addr.append (format_addr (upper_id, _host, _host_list))
			env.up_bw.append (np_bw [a ['id'] - 1] [int (upper_id) - 1])
		# 占位
		env.sync.append (a ['sync'])
		env.down_count.append (a ['dc'])
		env.current_down.append (0)
		# 是后面a[dc]个的父节点
		for _ in range (a ['dc']):
			upper_queue.append (a ['id'])
		# 让父节点连上自己
		if len (queue) != 0:
			u_e = env_map [queue.popleft ()]
			# 在父节点的第curr个子节点集合
			curr = 0
			while u_e.current_down [curr] == u_e.down_count [curr]:
				curr = curr + 1
			if curr == len (u_e.down_addr):
				u_e.down_addr.append ([])
				u_e.down_bw.append ([])
			if u_e.id == a ['id']:
				u_e.down_addr [curr].append ('self')
				u_e.down_bw [curr].append (0)
			else:
				u_e.down_addr [curr].append (format_addr (a ['id'], _host, _host_list))
				u_e.down_bw [curr].append (np_bw [a ['id'] - 1] [u_e.id - 1])
			u_e.current_down [curr] = u_e.current_down [curr] + 1
		# 是后面a[dc]个的父节点
		for _ in range (a ['dc']):
			queue.append (a ['id'])
		# 无子节点占位
		if a ['dc'] == 0:
			env_map [a ['id']].down_addr.append ([])
			env_map [a ['id']].down_bw.append ([])

	for index in env_map:
		file_name = './n' + str (env_map [index].id) + '.env'
		with open (file_name, 'w') as file:
			file.writelines (env_map [index].to_json ())


def gen_yml ():
	c_start = 1
	dep_index = 1
	for a in _host_list:
		# dep的信息
		str_dep = '---\r\n' \
		          + 'apiVersion: apps/v1\r\n' \
		          + 'kind: Deployment\r\n' \
		          + 'metadata:\r\n' \
		          + '  name: d-etree-' + str (dep_index) + '\r\n' \
		          + 'spec:\r\n' \
		          + '  selector:\r\n' \
		          + '    matchLabels:\r\n' \
		          + '      label: l-p-etree-' + str (dep_index) + '\r\n' \
		          + '  template: \r\n' \
		          + '    metadata:\r\n' \
		          + '      labels:\r\n' \
		          + '        label: l-p-etree-' + str (dep_index) + '\r\n' \
		          + '    spec:\r\n' \
		          + '      hostname: p-etree-' + str (dep_index) + '\r\n' \
		          + '      containers:\r\n'
		# dep中每个container的信息
		for c_index in range (c_start, a + 1):
			str_dep = str_dep \
			          + '      - name: n' + str (c_index) + '\r\n' \
			          + '        image: etree:v1.0\r\n' \
			          + '        imagePullPolicy: Never\r\n' \
			          + '        ports:\r\n' \
			          + '        - containerPort: ' + str (8000 + c_index) + '\r\n' \
			          + '        command: ["python3", "hybrid.py"]\r\n' \
			          + '        env:\r\n' \
			          + '        - name: HOSTNAME\r\n' \
			          + '          value: "n' + str (c_index) + '"\r\n' \
			          + '        - name: PORT\r\n' \
			          + '          value: "' + str (8000 + c_index) + '"\r\n' \
			          + '        volumeMounts:\r\n' \
			          + '        - name: etree\r\n' \
			          + '          mountPath: /home/etree\r\n'
		# dep中volume的信息
		str_dep = str_dep \
		          + '      volumes:\r\n' \
		          + '        persistentVolumeClaim:\r\n' \
		          + '          claimName: pvc-etree\r\n'
		# svc的信息
		str_dep = str_dep \
		          + '---\r\n' \
		          + 'apiVersion: v1\r\n' \
		          + 'kind: Service\r\n' \
		          + 'metadata:\r\n' \
		          + '  name: s-etree-' + str (dep_index) + '\r\n' \
		          + 'spec:\r\n' \
		          + '  selector:\r\n' \
		          + '    label: l-p-etree-' + str (dep_index) + '\r\n' \
		          + '  type: NodePort\r\n' \
		          + '  ports:\r\n'
		# svc中每个port的信息
		for c_index in range (c_start, a + 1):
			str_dep = str_dep \
			          + '  - name: n' + str (c_index) + '\r\n' \
			          + '    port: ' + str (8000 + c_index) + '\r\n' \
			          + '    targetPort: ' + str (8000 + c_index) + '\r\n' \
			          + '    nodePort: ' + str (30000 + c_index) + '\r\n'

		# 写入一个yml文件
		with open ('../master/dep-' + str (dep_index) + '.yml', 'w')as f:
			f.writelines (str_dep)
			f.close ()
		# 下一个文件用
		c_start = a + 1
		dep_index = dep_index + 1

	# bash运行脚本
	with open ('../master/dep.sh', 'w') as f:
		str_dep_sh = ''
		for i in range (dep_index - 1):
			str_dep_sh = str_dep_sh + 'kubectl delete -f dep-' + str (i + 1) + '.yml\r\n'
		for i in range (dep_index - 1):
			str_dep_sh = str_dep_sh + 'kubectl create -f dep-' + str (i + 1) + '.yml\r\n'
		f.writelines (str_dep_sh)
		f.close ()


# 读path的文件，json解析成list
_file = open ('env.txt')
_str = _file.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"')
_json = json.loads (_str)
_file.close ()

_list = _json ['list']
_host_list = _json ['host_list']
_host = 's-etree-'
if 'host' in _json:
	_host = _json ['host']

_round = _json ['round']
_local_epoch_num = _json ['local_epoch_num']
_batch_size = _json ['batch_size']
_learning_rate = _json ['learning_rate']
_start_index = _json ['start_index']
_end_index = _json ['end_index']
_worker_fraction = _json ['worker_fraction']

np_bw = np.loadtxt ('np_graph.txt')

# env对象
env_map = {}
# upper_id
upper_queue = deque (['top'])
# 待处理的env
queue = deque ([])

gen_env ()
gen_yml ()
