import getopt
import io
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request

import util
from nn import nn_lr
from values import values_h
from proxy import logact

nn = nn_lr.get_nn ()
v = values_h.get_values ()

# TODO: 这些都换掉==============
try:
	options, args = getopt.getopt (sys.argv [1:], 'i', ['id='])
except getopt.GetoptError:
	sys.exit ()

for option, value in options:
	if option in ('-i', '--id'):
		if int (value) == 0:
			v ['id'] = 0
			v ['port'] = 8888
			v ['type'] = 0
			# TODO: 当v ['type'] = 0时要同时设置v ['fraction'] = 1
			v ['layer_count'] = 3
			v ['layer'] = [1, 2, 3]
			v ['up_addr'] = ['http://localhost:8888', 'http://localhost:8888', 'top']
			v ['down_count'] = [0, 2, 2]
			v ['down_addr'] = [[], ['http://localhost:8888', 'http://localhost:8889'],
			                   ['http://localhost:8888', 'http://localhost:8890']]
			v ['round'] = 20
			v ['current_round'] = [0, 0, 0]
			v ['sync'] = [0, 2, 10]
			v ['received_count'] = [0, 0, 0]
			v ['received_weight'] = [[], [], []]
		elif int (value) == 1:
			v ['id'] = 1
			v ['port'] = 8889
			v ['type'] = 0
			v ['layer_count'] = 1
			v ['layer'] = [1]
			v ['up_addr'] = ['http://localhost:8888']
			v ['down_count'] = [0]
			v ['round'] = 20
			v ['current_round'] = [0]
			v ['sync'] = [0]
		elif int (value) == 2:
			v ['id'] = 2
			v ['port'] = 8890
			v ['type'] = 0
			v ['layer_count'] = 2
			v ['layer'] = [1, 2]
			v ['up_addr'] = ['http://localhost:8890', 'http://localhost:8888']
			v ['down_count'] = [0, 2]
			v ['down_addr'] = [[], ['http://localhost:8890', 'http://localhost:8891']]
			v ['round'] = 20
			v ['current_round'] = [0, 0]
			v ['sync'] = [0, 2]
			v ['received_count'] = [0, 0]
			v ['received_weight'] = [[], []]
		elif int (value) == 3:
			v ['id'] = 3
			v ['port'] = 8891
			v ['type'] = 0
			v ['layer_count'] = 1
			v ['layer'] = [1]
			v ['up_addr'] = ['http://localhost:8890']
			v ['down_count'] = [0]
			v ['round'] = 20
			v ['current_round'] = [0]
			v ['sync'] = [0]
if len (args) > 0:
	print ('error args: {0}'.format (args))

# for worker_index in range (v ['worker_num']):
# 	v ['worker_addr_list'].append ('http://localhost:' + str (v ['worker_port'] + worker_index))
# TODO: 这些都换掉==============


logging.basicConfig (level=logging.INFO, filename='log/node' + str (v ['id']) + '.log', filemode='w',
	format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')

# TODO: 从yml文件中读环境变量，设置v的一堆东西
#  EL中的round好像有点奇怪，下层节点要做多少次训练取决于父节点的同步频率...
#  也可以选择固定最底层节点的训练次数，上面的就随缘了
nn_lr.set_train_data_batch (v ['batch_size'], v ['round'], v ['start_index'], v ['end_index'])
nn_lr.set_train_lr (v ['learning_rate'])

lock = threading.Lock ()
app = Flask (__name__)
executor = ThreadPoolExecutor (1)
write = io.BytesIO ()


# 聚合
@app.route ('/start', methods=['GET'])
def start ():
	logging.info ('round 0: accuracy={}'.format (
		nn ['sess'].run (nn ['accuracy'], feed_dict={nn ['xs']: nn ['test_x'], nn ['ys']: nn ['test_y']})))
	initial_weights = nn ['sess'].run (nn ['weights'])

	from_layer = request.args.get ('layer', default=-1, type=int)

	# 从-1来，证明自己是EL的根节点，往下全发，send_weight_down_to_combine
	if from_layer == -1:
		self_layer = v ['layer'] [-1]
		util.send_weight_down_replace (write, initial_weights, v ['down_addr'] [-1], self_layer)
		return 'start EL\n'

	# 从0来，证明自己是FL的根节点，往下随机发，send_weight_down_to_train
	elif from_layer == 0:
		i_random = util.index_random (v ['down_count'] [0], v ['fraction'])
		util.send_weight_down_train (write, initial_weights, i_random, v ['down_addr'] [0])
		return 'start FL\n'

	return 'error \n'


# 聚合
@app.route ('/replace', methods=['POST'])
def route_replace ():
	file_w = request.files.get ('weights')
	from_layer = request.args.get ('layer', default=1, type=int)
	self_layer = from_layer - 1
	layer_index = v ['layer'].index (self_layer)

	# EL的第2层，下一层是训练节点，往下全发，send_weight_down_to_train
	if self_layer == 2:
		i_full = util.index_full (v ['down_count'] [layer_index])
		util.send_weight_down_train (write, file_w, i_full, v ['down_addr'] [layer_index], is_file=1)
	# EL的中间层，往下全发，send_weight_down_to_combine
	else:
		util.send_weight_down_replace (write, file_w, v ['down_addr'] [layer_index], self_layer, is_file=1)
	return ''


# 聚合
@app.route ('/combine', methods=['POST'])
def route_combine ():
	w = util.parse_received_weight (request.files.get ('weights'))
	from_layer = request.args.get ('layer', default=1, type=int)
	self_layer = from_layer + 1
	layer_index = v ['layer'].index (self_layer)

	# 接收参数并存起来
	global lock
	lock.acquire ()
	# 追加worker的参数到received_weight
	v ['received_weight'] [layer_index].append (w)
	v ['received_count'] [layer_index] += 1
	lock.release ()

	# 在EL中要确保v ['fraction'] = 1
	if v ['received_count'] [layer_index] == int (v ['down_count'] [layer_index] * v ['fraction']):
		executor.submit (on_route_combine, layer_index)
	return ''


# 聚合
def on_route_combine (layer_index):
	avg_weight = util.calculate_avg_weight (v ['received_weight'], v ['received_count'])
	v ['received_weight'] [layer_index].clear ()
	v ['received_count'] [layer_index] = 0
	util.assignment (nn ['assign_list'], avg_weight, nn ['sess'])
	v ['current_round'] [layer_index] += 1
	# 测试一下效果，写日志，清缓存
	logging.info ('round {}:accuracy={}'.format (v ['current_round'] [layer_index],
		nn ['sess'].run (nn ['accuracy'], feed_dict={nn ['xs']: nn ['test_x'], nn ['ys']: nn ['test_y']})))

	# EL
	if v ['type'] == 0:
		self_layer = v ['layer'] [layer_index]
		# 达到该层的sync，往上发
		if v ['current_round'] [layer_index] == v ['sync'] [layer_index]:
			# 是最高层
			if v ['up_addr'] [layer_index] == 'top':
				logact ().star3 ()
				logact ().star4 ()
				print ('===================training ended===================')
			# 不是最高层
			else:
				util.send_weight_up_combine (write, avg_weight, v ['up_addr'] [layer_index], self_layer)

		# 没达到该层的sync，往下发
		else:
			# EL的第2层，下一层是训练节点，往下全发，send_weight_down_to_train
			if self_layer == 2:
				i_full = util.index_full (v ['down_count'] [layer_index])
				util.send_weight_down_train (write, avg_weight, i_full, v ['down_addr'] [layer_index])
			# EL的中间层，往下全发，send_weight_down_to_combine
			else:
				util.send_weight_down_replace (write, avg_weight, v ['down_addr'] [layer_index], self_layer)

	# FL
	else:
		# 训练完
		if v ['current_round'] [layer_index] == v ['sync'] [0]:
			logact ().star3 ()
			logact ().star4 ()
			print ('===================training ended===================')

		# 没训练完
		else:
			i_random = util.index_random (v ['down_count'] [0], v ['fraction'])
			util.send_weight_down_train (write, avg_weight, i_random, v ['down_addr'] [0])


# 训练
@app.route ('/train', methods=['POST'])
def route_train ():
	w = util.parse_received_weight (request.files.get ('weights'))
	executor.submit (on_route_train, w)
	return ''


# 训练
def on_route_train (received_w):
	util.assignment (nn ['assign_list'], received_w, nn ['sess'])
	final_loss = util.train (v ['local_epoch_num'], nn ['batch_num'], nn ['sess'], nn ['batch'], nn ['loss'],
		nn ['train_step'], nn ['xs'], nn ['ys'])

	# 训练的时候肯定是作为最底层的节点
	v ['current_round'] [0] += 1
	logging.info ('worker {} round {}:loss={}'.format (v ['port'], v ['current_round'] [0], final_loss))

	latest_weights = nn ['sess'].run (nn ['weights'])
	util.send_weight_up_combine (write, latest_weights, v ['up_addr'] [0])


# 训练
@app.route ('/heart_beat', methods=['GET'])
def route_heart_beat ():
	return 'alive'


app.run (host='0.0.0.0', port=v ['self_port'], threaded=True, )
