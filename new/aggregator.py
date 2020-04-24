import getopt
import io
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request

import util
from nn import nn_lr
from values import values_a
from proxy import logact

nn = nn_lr.get_nn ()
v = values_a.get_values ()

logging.basicConfig (level=logging.INFO, filename='log/parameter_server.log', filemode='w',
	format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')

try:
	options, args = getopt.getopt (sys.argv [1:], 'n:f:r:', ['worker_num=', 'fraction=', 'round='])
except getopt.GetoptError:
	sys.exit ()

for option, value in options:
	if option in ('-n', '--worker_num'):
		v ['worker_num'] = int (value)
	elif option in ('-f', '--fraction'):
		v ['fraction'] = float (value)
	elif option in ('-r', '--round'):
		v ['round'] = int (value)
if len (args) > 0:
	print ('error args: {0}'.format (args))

for worker_index in range (v ['worker_num']):
	v ['worker_addr_list'].append ('http://localhost:' + str (v ['worker_port'] + worker_index))

lock = threading.Lock ()
app = Flask (__name__)
executor = ThreadPoolExecutor (1)
write = io.BytesIO ()


@app.route ('/start', methods=['GET'])
def start ():
	logging.info ('round 0: accuracy={}'.format (
		nn ['sess'].run (nn ['accuracy'], feed_dict={nn ['xs']: nn ['test_x'], nn ['ys']: nn ['test_y']})))
	initial_weights = nn ['sess'].run (nn ['weights'])
	selected_index = util.index_random (v ['worker_num'], v ['fraction'])
	util.send_weight_down_train (write, initial_weights, selected_index, v ['worker_addr_list'])
	return 'start\n'


@app.route ('/combine', methods=['POST'])
def route_combine ():
	# 接收参数并存起来
	global lock
	lock.acquire ()
	# 追加worker的参数到received_weight
	v ['received_weight'].append (util.parse_received_weight (request.files.get ('weights')))
	v ['received_count'] += 1
	lock.release ()
	# 判断一下接收够了没有
	if v ['received_count'] == int (v ['worker_num'] * v ['fraction']):
		executor.submit (on_route_combine)
	return 'server gets local weight'


def on_route_combine ():
	avg_weight = util.calculate_avg_weight (v ['received_weight'], v ['received_count'])
	v ['received_weight'].clear ()
	v ['received_count'] = 0
	util.assignment (nn ['assign_list'], avg_weight, nn ['sess'])
	v ['current_round'] += 1
	# 测试一下效果，写日志，清缓存
	logging.info ('round {}:accuracy={}'.format (v ['current_round'],
		nn ['sess'].run (nn ['accuracy'], feed_dict={nn ['xs']: nn ['test_x'], nn ['ys']: nn ['test_y']})))

	if v ['current_round'] == v ['round']:
		logact ().star3 ()
		logact ().star4 ()
		print (
			'=============================================================training ended====================================================================')
		return 'training ended'

	selected_index = util.index_random (v ['worker_num'], v ['fraction'])
	util.send_weight_down_train (write, avg_weight, selected_index, v ['worker_addr_list'])


app.run (host='0.0.0.0', port=v ['self_port'], threaded=True, )
