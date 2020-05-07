import json
import os

values = {}

values ['id'] = int (os.getenv ('id'), 0)
values ['port'] = int (os.getenv ('port'), 0)
values ['type'] = int (os.getenv ('type'), 0)
# TODO: 最顶层节点聚合多少次结束训练，该功能已被values ['sync']替代
#  目前的作用好像是用来将训练数据划分成一定数量的batch，考虑换个名称
values ['round'] = int (os.getenv ('round'))
# 每层的当前轮次
values ['layer_count'] = int (os.getenv ('layer_count', 0))
values ['layer'] = (json.loads (os.getenv ('layer'))) ['data']
values ['up_addr'] = (json.loads (os.getenv ('up_addr'))) ['data']
values ['down_count'] = (json.loads (os.getenv ('down_count'))) ['data']
if not (values ['layer_count'] == 1 and values ['layer'] [0] == 1):
	values ['down_addr'] = (json.loads (os.getenv ('down_addr'))) ['data']
values ['current_round'] = [0] * values ['layer_count']

# 聚合用
# FL中选择下一次训练的节点数量比例，在EL中应该设置为1
values ['fraction'] = 1
# EL中每层的同步频率
values ['sync'] = (json.loads (os.getenv ('sync'))) ['data']
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
