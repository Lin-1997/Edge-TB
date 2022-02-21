import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from flask import Flask, request

import dml_utils
import worker_utils
from nns.nn_fashion_mnist import nn  # configurable parameter, from nns.whatever import nn.

dirname = os.path.abspath (os.path.dirname (__file__))

dml_port = os.getenv ('DML_PORT')
ctl_addr = os.getenv ('NET_CTL_ADDRESS')
agent_addr = os.getenv ('NET_AGENT_ADDRESS')
node_name = os.getenv ('NET_NODE_NAME')

initial_weights = nn.model.get_weights ()
input_shape = nn.input_shape
log_file = os.path.abspath (os.path.join (dirname, '../dml_file/log/', node_name + '.log'))
worker_utils.set_log (log_file)
conf = {}
trainer_list = []
trainer_per_round = 0
# configurable parameter, specify the dataset path.
test_path = os.path.join (dirname, '../dataset/FASHION_MNIST/test_data')
test_images: np.ndarray
test_labels: np.ndarray

app = Flask (__name__)
lock = threading.RLock ()
executor = ThreadPoolExecutor (1)


# if this is container, docker will send a GET to here every 30s
# this ability is defined in controller/base/node.py, Class Emulator, save_yml (), healthcheck.
@app.route ('/hi', methods=['GET'])
def route_hi ():
	# send a heartbeat to the agent.
	# when the agent receives the heartbeat of a container for the first time,
	# it will deploy the container's tc settings.
	# please ensure that your app implements this function, i.e.,
	# receiving docker healthcheck and sending heartbeat to the agent.
	worker_utils.heartbeat (agent_addr, node_name)
	return 'this is node ' + node_name + '\n'


@app.route ('/conf/dataset', methods=['POST'])
def route_conf_d ():
	f = request.files.get ('conf').read ()
	conf.update (json.loads (f))
	print ('POST at /conf/dataset')

	global test_images, test_labels
	test_images, test_labels = dml_utils.load_data (test_path, conf ['test_start_index'],
		conf ['test_len'], input_shape)

	filename = os.path.join (dirname, '../dml_file/conf', node_name + '_dataset.conf')
	with open (filename, 'w') as fw:
		fw.writelines (json.dumps (conf, indent=2))
	return ''


@app.route ('/conf/structure', methods=['POST'])
def route_conf_s ():
	f = request.files.get ('conf').read ()
	conf.update (json.loads (f))
	print ('POST at /conf/structure')

	filename = os.path.join (dirname, '../dml_file/conf', node_name + '_structure.conf')
	with open (filename, 'w') as fw:
		fw.writelines (json.dumps (conf, indent=2))

	global trainer_per_round
	conf ['current_round'] = 0
	conf ['received_number'] = 0
	conf ['received_weights'] = []
	trainer_list.extend (conf ['child_node'])
	trainer_per_round = int (len (trainer_list) * conf ['trainer_fraction'])
	return ''


# for customized selection >>>

total_time = {}
send_time = {}
name_list = []
prob_list = []


@app.route ('/time/train', methods=['GET'])
def route_time_train ():
	print ('GET at /time/train')
	node = request.args.get ('node')
	_time = request.args.get ('time', type=float)
	print ('train: ' + node + ' use ' + str (_time))
	with lock:
		total_time [node] = _time
		if len (total_time) == len (trainer_list):
			file_path = os.path.join (dirname, '../dml_file/train_time.txt')
			with open (file_path, 'w') as f:
				f.write (json.dumps (total_time))
				print ('train time collection completed, saved on ' + file_path)
	return ''


@app.route ('/time/test', methods=['POST'])
def route_stest ():
	print ('POST at /time/test')
	# trainer sends weights to here, so it can get the time for sending.
	_ = dml_utils.parse_weights (request.files.get ('weights'))
	return ''


@app.route ('/time/send', methods=['GET'])
def route_time_send ():
	print ('GET at /time/send')
	node = request.args.get ('node')
	_time = request.args.get ('time', type=float)
	print ('send: ' + node + ' use ' + str (_time))
	with lock:
		send_time [node] = _time
		if len (send_time) == len (trainer_list):
			file_path = os.path.join (dirname, '../dml_file/send_time.txt')
			with open (file_path, 'w') as f:
				f.write (json.dumps (send_time))
				print ('send time collection completed, saved on ' + file_path)

			count = 0
			for node in total_time:
				total_time [node] += send_time [node]
			file_path = os.path.join (dirname, '../dml_file/total_time.txt')
			with open (file_path, 'w') as f:
				f.write (json.dumps (total_time))
				print ('total time collection completed, saved on ' + file_path)
			for node in total_time:
				total_time [node] = 1 / (total_time [node] ** 0.5)
				count += total_time [node]
			for node in total_time:
				name_list.append (node)
				prob_list.append (round (total_time [node] / count, 3) * 1000)
			count = 0
			for i in range (len (prob_list)):
				count += prob_list [i]
			prob_list [-1] += 1000 - count
			for i in range (len (prob_list)):
				prob_list [i] /= 1000
			print ('prob_list = ')
			print (prob_list)
	return ''


def customized_selection (number):
	return np.random.choice (name_list, number, p=prob_list, replace=False)


# <<< for customized selection

@app.route ('/log', methods=['GET'])
def route_log ():
	executor.submit (on_route_log)
	return ''


def on_route_log ():
	worker_utils.send_log (ctl_addr, log_file, node_name)


@app.route ('/start', methods=['GET'])
def route_start ():
	print ('GET at /start')
	executor.submit (on_route_start)
	return ''


def on_route_start ():
	_, init_acc = dml_utils.test_on_batch (nn.model, test_images, test_labels, conf ['batch_size'])
	msg = dml_utils.log_acc (init_acc, 0, conf ['layer'] [-1])
	worker_utils.send_print (ctl_addr, node_name + ': ' + msg)

	# trainers = dml_utils.random_selection (trainer_list, trainer_per_round)
	trainers = customized_selection (trainer_per_round)
	dml_utils.send_weights (initial_weights, '/train', trainers, conf ['connect'])
	worker_utils.send_print (ctl_addr, 'start FL')


# combine request from the lower layer node.
@app.route ('/combine', methods=['POST'])
def route_combine ():
	print ('POST at /combine')
	weights = dml_utils.parse_weights (request.files.get ('weights'))
	executor.submit (on_route_combine, weights)
	return ''


def on_route_combine (weights):
	with lock:
		conf ['received_number'] += 1
		dml_utils.store_weights (conf ['received_weights'], weights,
			conf ['received_number'])

		if conf ['received_number'] == trainer_per_round:
			combine_weights ()


def combine_weights ():
	weights = dml_utils.avg_weights (conf ['received_weights'], conf ['received_number'])
	dml_utils.assign_weights (nn.model, weights)
	conf ['received_weights'].clear ()
	conf ['received_number'] = 0
	conf ['current_round'] += 1

	_, acc = dml_utils.test (nn.model, test_images, test_labels)
	msg = dml_utils.log_acc (acc, conf ['current_round'])
	worker_utils.send_print (ctl_addr, node_name + ': ' + msg)

	if conf ['current_round'] == conf ['sync']:
		worker_utils.log ('>>>>>training ended<<<<<')
		worker_utils.send_data ('GET', '/finish', ctl_addr)
	else:  # send down to train.
		# trainers = dml_utils.random_selection (trainer_list, trainer_per_round)
		trainers = customized_selection (trainer_per_round)
		dml_utils.send_weights (weights, '/train', trainers, conf ['connect'])


app.run (host='0.0.0.0', port=dml_port, threaded=True)
