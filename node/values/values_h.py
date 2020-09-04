import json
import os


def read_env ():
	file_name = os.getenv ('HOSTNAME') + '.env'
	file_path = os.path.abspath (os.path.join (os.path.dirname (__file__), '../env', file_name))
	file = open (file_path)
	env = json.loads (file.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))
	file.close ()
	return env


def get_values ():
	return values


values = read_env ()
values ['current_round'] = [0] * values ['layer_count']
# 从MB/s变成B/s
for key in values ['bw'].keys ():
	values ['bw'] [key] = 1024 * 1024 * values ['bw'] [key]

# 聚合用
# 每层接收到的参数数量
values ['received_count'] = [0] * values ['layer_count']
# 每层接收到的参数
values ['received_weight'] = [[] for i in range (values ['layer_count'])]

# FL聚合节点专用，每轮选多少比例的节点训练，EL中赋值为1
if values ['type'] == 0:
	values ['worker_fraction'] = 1
