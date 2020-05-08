import json
import os

file_name = os.getenv ('HOSTNAME') + '.env'
file_path = os.path.abspath (os.path.join (os.path.dirname (__file__), '../env', file_name))
file = open (file_path)
values = json.loads (file.read ().replace ('\n', '').replace ('\r', ''))

if int (os.getenv ('FROMYML', default=0)) == 1:
	if 'up_addr_host' in values:
		values ['up_addr'] = values ['up_addr_host']
		print ('change up')
	if 'down_addr_host' in values:
		values ['down_addr'] = values ['down_addr_host']
		print ('change down')

values ['current_round'] = [0] * values ['layer_count']
# 聚合用
# FL中选择下一次训练的节点数量比例，在EL中应该设置为1
values ['fraction'] = 1
# 每层接收到的参数数量
values ['received_count'] = [0] * values ['layer_count']
# 每层接收到的参数
values ['received_weight'] = [[] for i in range (values ['layer_count'])]

# TODO: 还没写到env
# 训练用
values ['batch_size'] = 1
values ['local_epoch_num'] = 1
values ['learning_rate'] = 0.1
# 训练样本范围
values ['start_index'] = 0
values ['end_index'] = 1


def get_values ():
	return values
