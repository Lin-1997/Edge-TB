import io
import os
import threading
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request

import util
from nns import nn_lr
from values import values_h

util.set_log (os.getenv ('HOSTNAME'))
v = values_h.get_values ()
nn = nn_lr.get_nn ()

if 'learning_rate' in v and v ['learning_rate'] != 0:
	nn_lr.set_train_lr (v ['learning_rate'])
	nn_lr.set_train_data_batch (v ['batch_size'], v ['round'], v ['start_index'], v ['end_index'])

app = Flask (__name__)
weights_lock = threading.Lock ()
executor = ThreadPoolExecutor (1)


@app.route ('/hi', methods=['GET'])
def route_hi ():
	return 'Node ' + os.getenv ('HOSTNAME') + ' in ' + str (os.getenv ('PORT')) + '\r\r\n'


# 聚合
@app.route ('/start', methods=['GET'])
def route_start ():
	initial_weights = nn ['sess'].run (nn ['weights'])
	from_layer = request.args.get ('layer', default=-1, type=int)

	# 从-1来，证明自己是EL的根节点，往下全发，path=replace
	if from_layer == -1:
		self_layer = v ['layer'] [-1]
		i_full = util.index_full (v ['down_count'] [-1])
		send_self = util.send_weight (initial_weights, i_full, v ['down_host'] [-1], v ['node'], v ['forward'],
			v ['bw'], '/replace', layer=self_layer)
		if send_self == 1:
			on_route_replace (initial_weights, self_layer)
		return 'start EL\r\n'

	# 从0来，证明自己是FL的根节点，往下随机发，path=train
	elif from_layer == 0:
		i_random = util.index_random (v ['down_count'] [0], v ['worker_fraction'])
		util.send_weight (initial_weights, i_random, v ['down_host'] [0], v ['node'], v ['forward'], v ['bw'], '/train')
		return 'start FL\r\n'

	return 'error\r\n'


# 聚合
@app.route ('/replace', methods=['POST'])
def route_replace ():
	file_w = request.files.get ('weights')
	from_layer = request.args.get ('layer', type=int)
	s_time = request.args.get ('time', type=float)
	bw = request.args.get ('bw', type=float)

	temp_file = io.BytesIO ()
	file_w.save (temp_file)
	file_w.seek (0)
	size = len (file_w.read ())  # 模拟网络传输时延
	temp_file.seek (0)

	executor.submit (on_route_replace, temp_file, from_layer, is_binary=1,
		size=size, s_time=s_time, bw=bw)
	return ''


def on_route_replace (w, from_layer, is_binary=0, size=0, s_time=0.0, bw=0):
	if size != 0:
		util.simulate_sleep (size, s_time, bw)

	self_layer = from_layer - 1
	layer_index = v ['layer'].index (self_layer)
	i_full = util.index_full (v ['down_count'] [layer_index])

	# EL的第2层，下一层是训练节点，往下全发，path=train
	if self_layer == 2:
		send_self = util.send_weight (w, i_full, v ['down_host'] [layer_index], v ['node'], v ['forward'], v ['bw'],
			'/train', is_binary=is_binary)
		if send_self == 1:
			on_route_train (w, is_binary=is_binary)
	# EL的中间层，往下全发，path=replace
	else:
		send_self = util.send_weight (w, i_full, v ['down_host'] [layer_index], v ['node'], v ['forward'],
			v ['bw'], '/replace', layer=self_layer, is_binary=is_binary)
		if send_self == 1:
			on_route_replace (w, self_layer, is_binary=is_binary)


# 聚合
@app.route ('/combine', methods=['POST'])
def route_combine ():
	file_w = request.files.get ('weights')
	from_layer = request.args.get ('layer', type=int)
	s_time = request.args.get ('time', type=float)
	bw = request.args.get ('bw', type=float)

	temp_file = io.BytesIO ()
	file_w.save (temp_file)
	file_w.seek (0)
	size = len (file_w.read ())  # 模拟网络传输时延
	temp_file.seek (0)

	w = util.parse_received_weight (temp_file)
	executor.submit (on_route_combine, w, from_layer, size=size, s_time=s_time, bw=bw)
	return ''


def on_route_combine (w, from_layer, size=0, s_time=0.0, bw=0):
	if size != 0:
		util.simulate_sleep (size, s_time, bw)

	self_layer = from_layer + 1
	layer_index = v ['layer'].index (self_layer)

	# 接收参数并存起来
	global weights_lock
	weights_lock.acquire ()
	# 追加worker的参数到received_weight
	v ['received_weight'] [layer_index].append (w)
	v ['received_count'] [layer_index] += 1
	weights_lock.release ()

	# 在EL中要确保v ['worker_fraction'] = 1
	if v ['received_count'] [layer_index] == int (v ['down_count'] [layer_index] * v ['worker_fraction']):
		combine_weight (layer_index)


# 聚合
def combine_weight (layer_index):
	avg_weight = util.calculate_avg_weight (v ['received_weight'] [layer_index], v ['received_count'] [layer_index])
	v ['received_weight'] [layer_index].clear ()
	v ['received_count'] [layer_index] = 0
	util.assignment (nn ['assign_list'], avg_weight, nn ['sess'])
	v ['current_round'] [layer_index] += 1
	# 测试一下效果，写日志，清缓存
	util.log ('Aggregate: layer={}, round={}, sync={}, accuracy={}'.format (
		v ['layer'] [layer_index], v ['current_round'] [layer_index], v ['sync'] [layer_index],
		nn ['sess'].run (nn ['accuracy'], feed_dict={nn ['xs']: nn ['test_x'], nn ['ys']: nn ['test_y']})))

	# EL
	if v ['type'] == 0:
		self_layer = v ['layer'] [layer_index]
		# 达到该层的sync，往上发
		if v ['current_round'] [layer_index] % v ['sync'] [layer_index] == 0:
			# 是最高层
			if v ['up_host'] [layer_index] == 'top':
				# 用没有GUI的云服务器下面两句代码会卡死
				# 用有GUI的设备可以正常使用
				# 输出训练的accuracy和loss图像
				# logact ().star3 ()
				# logact ().star4 ()
				print ('===================training ended===================')
			# 不是最高层
			else:
				send_self = util.send_weight (avg_weight, [layer_index], v ['up_host'], v ['node'], v ['forward'],
					v ['bw'], '/combine', layer=self_layer)
				if send_self == 1:
					on_route_combine (avg_weight, self_layer)

		# 没达到该层的sync，往下发
		else:
			i_full = util.index_full (v ['down_count'] [layer_index])
			# EL的第2层，下一层是训练节点，往下全发，path=train
			if self_layer == 2:
				send_self = util.send_weight (avg_weight, i_full, v ['down_host'] [layer_index], v ['node'],
					v ['forward'], v ['bw'], '/train')
				if send_self == 1:
					on_route_train (avg_weight)
			# EL的中间层，往下全发，path=replace
			else:
				send_self = util.send_weight (avg_weight, i_full, v ['down_host'] [layer_index], v ['node'],
					v ['forward'], v ['bw'], '/replace', layer=self_layer)
				if send_self == 1:
					on_route_replace (avg_weight, self_layer)

	# FL
	else:
		# 训练完
		if v ['current_round'] [layer_index] == v ['sync'] [0]:
			# logact ().star3 ()
			# logact ().star4 ()
			print ('===================training ended===================')

		# 没训练完
		else:
			i_random = util.index_random (v ['down_count'] [0], v ['worker_fraction'])
			util.send_weight (avg_weight, i_random, v ['down_host'] [0], v ['node'], v ['forward'], v ['bw'], '/train')


# 训练
@app.route ('/train', methods=['POST'])
def route_train ():
	file_w = request.files.get ('weights')
	s_time = request.args.get ('time', type=float)
	bw = request.args.get ('bw', type=float)

	temp_file = io.BytesIO ()
	file_w.save (temp_file)
	file_w.seek (0)
	size = len (file_w.read ())  # 模拟网络传输时延
	temp_file.seek (0)

	executor.submit (on_route_train, temp_file, is_binary=1, size=size, s_time=s_time, bw=bw)
	return ''


# 训练
def on_route_train (received_w, is_binary=0, size=0, s_time=0.0, bw=0):
	if size != 0:
		util.simulate_sleep (size, s_time, bw)

	if is_binary == 1:
		w = util.parse_received_weight (received_w)
		util.assignment (nn ['assign_list'], w, nn ['sess'])
	else:
		util.assignment (nn ['assign_list'], received_w, nn ['sess'])
	final_loss = util.train (v ['local_epoch_num'], nn ['batch_num'], nn ['sess'], nn ['batch'], nn ['loss'],
		nn ['train_step'], nn ['xs'], nn ['ys'])

	# 训练的时候肯定是作为最底层的节点
	v ['current_round'] [0] += 1
	util.log ('Train: round={}:loss={}'.format (v ['current_round'] [0], final_loss))

	latest_weights = nn ['sess'].run (nn ['weights'])
	send_self = util.send_weight (latest_weights, [0], v ['up_host'], v ['node'], v ['forward'], v ['bw'], '/combine',
		layer=1)
	if send_self == 1:
		on_route_combine (latest_weights, 1)


@app.route ('/forward', methods=['POST'])
def route_forward ():
	weights = request.files.get ('weights')
	data = {'host': request.form ['host'],
	        'path': request.form ['path'],
	        'layer': request.form.get ('layer')}
	s_time = request.args.get ('time', type=float)
	bw = request.args.get ('bw', type=float)

	temp_file = io.BytesIO ()
	weights.save (temp_file)
	weights.seek (0)
	size = len (weights.read ())  # 模拟网络传输时延
	temp_file.seek (0)

	executor.submit (on_route_forward, temp_file, data, size, s_time, bw)
	return ''


def on_route_forward (weights, data, size, _time, bw):
	util.simulate_sleep (size, _time, bw)
	if data ['host'] in v ['node']:
		addr = v ['node'] [data ['host']]
		util.send (weights, data, addr, v ['bw'] [addr], is_forward=False)
	else:
		addr = v ['forward'] [data ['host']]
		util.send (weights, data, addr, v ['bw'] [addr], is_forward=True)


app.run (host='0.0.0.0', port=os.getenv ('PORT'), threaded=True)
