import getopt
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request

import nn_test_lr
import util
import values_a

v = values_a.get_values ()
nn = nn_test_lr.get_nn ()

logging.basicConfig (level=logging.INFO, filename='log/parameter_server.log', filemode='w',
                     format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')

lock = threading.Lock ()

try:
	options, args = getopt.getopt (sys.argv [1:], "n:c:r:", ["client_num=", "fraction=", "round="])
except getopt.GetoptError:
	sys.exit ()

for option, value in options:
	if option in ("-n", "--client_num"):
		v ['client_num'] = int (value)
	elif option in ("-c", "--fraction"):
		v ['fraction'] = float (value)
	elif option in ("-r", "--round"):
		v ['round'] = int (value)
if len (args) > 0:
	print ("error args: {0}".format (args))

for client_index in range (v ['client_num']):
	v ['addr'].append (v ['start_port'] + client_index)

app = Flask (__name__)
executor = ThreadPoolExecutor (1)


@app.route ('/combine_weight', methods=['POST'])
def receive_weight ():
	# 接收参数并存起来
	if v ['current_round'] == v ['round']:
		print (
			"=============================================================training ended====================================================================")
		return "training ended"
	global lock
	lock.acquire ()
	# 追加client的参数到received_client_weight
	util.save_received_weight (v ['received_weight'], request.files.get ('client_weights'))
	# logging.info("received weights: {}".format(received_weight[0]))
	v ['received_count'] += 1
	lock.release ()
	# 判断一下接收够了没有
	if v ['received_count'] == int (v ['client_num'] * v ['fraction']):
		executor.submit (on_receive_weight)
	return "server gets local weight"


def on_receive_weight ():
	avg_weight = util.calculate_avg_weight (v ['received_weight'], v ['received_count'])
	v ['received_weight'].clear ()
	v ['received_count'] = 0
	util.assignment (nn ['assign_list'], avg_weight, nn ['sess'])
	# 测试一下效果，写日志，清缓存
	logging.info ('round {}:accuracy={}'.format (v ['current_round'], nn ['sess'].run (nn ['accuracy'], feed_dict={
		nn ['xs']: nn ['test_x'], nn ['ys']: nn ['test_y']})))
	client_list = util.client_list_random (v ['client_num'], v ['fraction'])
	util.send_weight (avg_weight, client_list, v ['addr'])
	v ['current_round'] += 1


@app.route ('/start', methods=['GET'])
def start ():
	logging.info ('round 0: accuracy={}'.format (nn ['sess'].run (nn ['accuracy'], feed_dict={
		nn ['xs']: nn ['test_x'], nn ['ys']: nn ['test_y']})))
	initial_weights = nn ['sess'].run (nn ['weights'])
	client_list = util.client_list_random (v ['client_num'], v ['fraction'])
	util.send_weight (initial_weights, client_list, v ['addr'])
	v ['current_round'] += 1
	return 'start\n'


app.run (port=8888, threaded=True)
