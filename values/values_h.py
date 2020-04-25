values = {}

values ['id'] = 0
values ['port'] = 8888
# type=0-EL 1-FL
values ['type'] = 0
# 同时处于多少层
values ['layer_count'] = 0
# TODO: 分别属于哪些层
# values ['layer'] = [] * l_c
# TODO: 每层的上层节点地址
# values ['up_addr'] = [] * l_c
# TODO: 每层的下层节点数量
# values ['down_count'] = [] * l_c
# TODO: 每层的下层节点地址
# values ['down_addr'] = [[] for i in range (l_c)]

# TODO: 最顶层节点聚合多少次结束训练，该功能已被values ['sync']替代
#  目前的作用好像是用来将训练数据划分成一定数量的batch，考虑换个名称
values ['round'] = 20
# TODO: 每层的当前轮次
# values ['current_round'] = [] * l_c

# 聚合用
# TODO: FL中选择下一次训练的节点数量比例，在EL中应该设置为1
values ['fraction'] = 1
# TODO: EL中每层的同步频率
# values ['sync'] = [] * l_c
# TODO: 每层接收到的参数数量
# values ['received_count'] = [] * l_c
# TODO: 每层接收到的参数
# values ['received_weight'] = [[] for i in range (l_c)]

# 训练用
values ['batch_size'] = 1
values ['local_epoch_num'] = 1
values ['learning_rate'] = 0.1
# 训练样本范围
values ['start_index'] = 0
values ['end_index'] = 1


def get_values ():
	return values
