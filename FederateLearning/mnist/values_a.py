values = {}

# default values
values ['client_num'] = 2
values ['fraction'] = 0.5
values ['round'] = 40
values ['current_round'] = 0

# 已回传参数的客户端数量
values ['received_count'] = 0
# 存放各客户端回传参数的列表
values ['received_weight'] = []

values ['start_port'] = 9990
values ['addr'] = []


def get_values ():
	return values
