import json
import os

file_name = os.getenv ('HOSTNAME') + '.env'
file_path = os.path.abspath (os.path.join (os.path.dirname (__file__), '../env', file_name))
file = open (file_path)
values = json.loads (file.read ().replace ('\n', '').replace ('\r', ''))

if int (os.getenv ('FROMYML', default=0)) == 1:
	if 'up_addr_host' in values:
		values ['up_addr'] = values ['up_addr_host']
	if 'down_addr_host' in values:
		values ['down_addr'] = values ['down_addr_host']

values ['current_round'] = [0] * values ['layer_count']

# 聚合用
# 每层接收到的参数数量
values ['received_count'] = [0] * values ['layer_count']
# 每层接收到的参数
values ['received_weight'] = [[] for i in range (values ['layer_count'])]

# FL聚合节点专用，每轮选多少比例的节点训练，EL中赋值为1
if values ['type'] == 0:
	values ['worker_fraction'] = 1


def get_values ():
	return values
