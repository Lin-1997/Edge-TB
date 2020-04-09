values = {}

values ['self_port'] = 8888

values ['worker_addr_list'] = []
values ['worker_port'] = 9990
values ['worker_num'] = 2

values ['round'] = 40
values ['current_round'] = 0
values ['fraction'] = 0.5

# 已回传参数的数量
values ['received_count'] = 0
# 存放各回传参数的列表
values ['received_weight'] = []


def get_values ():
	return values
