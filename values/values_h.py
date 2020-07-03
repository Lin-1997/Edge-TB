import json
import os


def read_env ():
	file_name = os.getenv ('HOSTNAME') + '.env'
	file_path = os.path.abspath (os.path.join (os.path.dirname (__file__), '../env', file_name))
	file = open (file_path)
	env = json.loads (file.read ().replace ('\n', '').replace ('\r', ''))
	file.close ()
	return env


def update_addr (v):
	env = read_env ()
	if 'up_addr' in env:
		v ['up_addr'] = env ['up_addr']
	if 'down_addr' in env:
		v ['down_addr'] = env ['down_addr']


def get_values ():
	return values


values = read_env ()
values ['current_round'] = [0] * values ['layer_count']

if values ['unit'] == 'KB':
	values ['bw'] = values ['bw'] * 1024
elif values ['unit'] == 'MB':
	values ['bw'] = values ['bw'] * 1024 * 1024

# 聚合用
# 每层接收到的参数数量
values ['received_count'] = [0] * values ['layer_count']
# 每层接收到的参数
values ['received_weight'] = [[] for i in range (values ['layer_count'])]

# FL聚合节点专用，每轮选多少比例的节点训练，EL中赋值为1
if values ['type'] == 0:
	values ['worker_fraction'] = 1
