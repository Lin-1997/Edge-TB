values = {}

values ['addr_a'] = 'http://localhost:8888'
values ['start_port'] = 9990

values ['round'] = 40
values ['current_round'] = 0
values ['batch_size'] = 1
values ['local_epoch_num'] = 1
values ['learning_rate'] = 0.1

# 训练样本范围
values ['start_index'] = 0
values ['end_index'] = 1


def get_values ():
	return values
