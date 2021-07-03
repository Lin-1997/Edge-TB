import io
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from flask import Flask, request

import dml_utils
import worker_utils
from nns.nn_fashion_mnist import nn  # configurable parameter, from nns.whatever import nn.

dirname = os.path.abspath (os.path.dirname (__file__))

# listen on port 4444.
# we do not recommend changing this port number.
dml_port = 4444

ctl_addr = os.getenv ('NET_CTL_ADDRESS')
agent_addr = os.getenv ('NET_AGENT_ADDRESS')
node_name = os.getenv ('NET_NODE_NAME')

initial_weights = nn.model.get_weights ()
input_shape = nn.input_shape
log_file = os.path.abspath (os.path.join (dirname, '../dml_file/log/',
	node_name + '.log'))
worker_utils.set_log (log_file)
conf = {}
# configurable parameter, specify the dataset path.
test_path = os.path.join (dirname, '../dataset/FASHION_MNIST/test_data')
test_images: np.ndarray
test_labels: np.ndarray
# configurable parameter, specify the dataset path.
train_path = os.path.join (dirname, '../dataset/FASHION_MNIST/train_data')
train_images: np.ndarray
train_labels: np.ndarray
t_time: float

app = Flask (__name__)
weights_lock = threading.Lock ()
executor = ThreadPoolExecutor (1)


# if this is container, docker will send a GET to here every 30s
# this ability is defined in controller/class_node.py, Emulator.save_yml (), healthcheck.
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

	global test_images, test_labels, train_images, train_labels
	if conf ['test_len'] > 0:
		test_images, test_labels = dml_utils.load_data (test_path, conf ['test_start_index'],
			conf ['test_len'], input_shape)
	if conf ['train_len'] > 0:
		train_images, train_labels = dml_utils.load_data (train_path, conf ['train_start_index'],
			conf ['train_len'], input_shape)
	executor.submit (perf_eval)

	filename = os.path.join (dirname, '../dml_file/conf', node_name + '_dataset.conf')
	with open (filename, 'w') as fw:
		fw.writelines (json.dumps (conf, indent=2))
	return ''


# performance evaluation for trainer.
def perf_eval ():
	global t_time
	if conf ['train_len'] > 0:
		s_time = time.time ()
		dml_utils.train (nn.model, train_images, train_labels, 1, conf ['batch_size'], conf ['train_len'])
		t_time = time.time () - s_time
		dml_utils.assign_weights (nn.model, initial_weights)
	else:
		t_time = -1.0  # not trainer.
	path = '/perf?node=' + node_name + '&time=' + str (t_time) + '&size=' + str (nn.size)
	worker_utils.send_data ('GET', path, ctl_addr)
	worker_utils.log (node_name + ': 1 epoch time=' + str (t_time))


@app.route ('/conf/structure', methods=['POST'])
def route_conf_s ():
	f = request.files.get ('conf').read ()
	conf.update (json.loads (f))
	print ('POST at /conf/structure')

	filename = os.path.join (dirname, '../dml_file/conf', node_name + '_structure.conf')
	with open (filename, 'w') as fw:
		fw.writelines (json.dumps (conf, indent=2))

	conf ['current_round'] = [0] * len (conf ['layer'])
	conf ['received_number'] = [0] * len (conf ['layer'])
	conf ['received_weights'] = [[] for _ in range (len (conf ['layer']))]
	return ''


@app.route ('/log', methods=['GET'])
def route_log ():
	executor.submit (on_route_log)
	return ''


def on_route_log ():
	worker_utils.send_log (ctl_addr, log_file, node_name)


def send_weights_down (weights, nodes, self_layer):
	if self_layer == 2:
		send_self = dml_utils.send_weights (weights, '/train', nodes, conf ['connect'],
			forward=conf ['forward'], layer=self_layer)
		if send_self == 1:
			worker_utils.log ('send self at /train')
			on_route_train (weights)

	elif self_layer > 2:
		send_self = dml_utils.send_weights (weights, '/replace', nodes, conf ['connect'],
			forward=conf ['forward'], layer=self_layer)
		if send_self == 1:
			worker_utils.log ('send self at /replace')
			on_route_replace (weights, self_layer)


@app.route ('/start', methods=['GET'])
def route_start ():
	_, initial_acc = dml_utils.test_on_batch (nn.model, test_images, test_labels, conf ['batch_size'])
	msg = dml_utils.log_acc (initial_acc, 0, conf ['layer'] [-1])
	worker_utils.send_print (ctl_addr, node_name + ': ' + msg)
	executor.submit (on_route_start)
	return ''


def on_route_start ():
	self_layer = conf ['layer'] [-1]
	nodes = conf ['child_node'] [-1]
	send_weights_down (initial_weights, nodes, self_layer)


# replace request from the upper layer node.
@app.route ('/replace', methods=['POST'])
def route_replace ():
	from_layer = request.form.get ('layer', type=int)
	print ('POST at /replace from layer ' + str (from_layer))
	weights = dml_utils.parse_weights (request.files.get ('weights'))
	executor.submit (on_route_replace, weights, from_layer)
	return ''


def on_route_replace (weights, from_layer):
	self_layer = from_layer - 1
	layer_index = conf ['layer'].index (self_layer)
	nodes = conf ['child_node'] [layer_index]
	send_weights_down (weights, nodes, self_layer)


# combine request from the lower layer node.
@app.route ('/combine', methods=['POST'])
def route_combine ():
	from_layer = request.form.get ('layer', type=int)
	print ('POST at /combine from layer ' + str (from_layer))
	weights = dml_utils.parse_weights (request.files.get ('weights'))
	executor.submit (on_route_combine, weights, from_layer)
	return ''


def on_route_combine (weights, from_layer):
	self_layer = from_layer + 1
	layer_index = conf ['layer'].index (self_layer)

	weights_lock.acquire ()
	conf ['received_number'] [layer_index] += 1
	dml_utils.store_weights (conf ['received_weights'] [layer_index], weights,
		conf ['received_number'] [layer_index])
	weights_lock.release ()

	if conf ['received_number'] [layer_index] == len (conf ['child_node'] [layer_index]):
		combine_weights (self_layer, layer_index)


def combine_weights (self_layer, layer_index):
	weights = dml_utils.avg_weights (conf ['received_weights'] [layer_index],
		conf ['received_number'] [layer_index])
	dml_utils.assign_weights (nn.model, weights)
	conf ['received_weights'] [layer_index].clear ()
	conf ['received_number'] [layer_index] = 0
	conf ['current_round'] [layer_index] += 1

	_, acc = dml_utils.test_on_batch (nn.model, test_images, test_labels, conf ['batch_size'])
	_round, layer = conf ['current_round'] [layer_index], conf ['layer'] [layer_index]
	msg = dml_utils.log_acc (acc, _round, layer)
	worker_utils.send_print (ctl_addr, node_name + ': ' + msg)

	# meet the sync of this layer, send up to combine.
	if conf ['current_round'] [layer_index] % conf ['sync'] [layer_index] == 0:
		# is the top node.
		if conf ['father_node'] [layer_index] == 'top':
			worker_utils.log ('>>>>>training ended<<<<<')
			worker_utils.send_data ('GET', '/finish', ctl_addr)
		# isn't the top node.
		else:
			send_self = dml_utils.send_weights (weights, '/combine', conf ['father_node'] [layer_index:layer_index + 1],
				conf ['connect'], forward=conf ['forward'], layer=self_layer)
			if send_self == 1:
				worker_utils.log ('send self at /combine')
				on_route_combine (weights, self_layer)

	# haven't meet the sync, send down.
	else:
		nodes = conf ['child_node'] [layer_index]
		send_weights_down (weights, nodes, self_layer)


# train request from the upper layer node.
@app.route ('/train', methods=['POST'])
def route_train ():
	print ('POST at /train')
	weights = dml_utils.parse_weights (request.files.get ('weights'))
	executor.submit (on_route_train, weights)
	return ''


def on_route_train (received_weights):
	dml_utils.assign_weights (nn.model, received_weights)
	loss_list = dml_utils.train (nn.model, train_images, train_labels,
		conf ['epoch'], conf ['batch_size'], conf ['train_len'])
	# must be the lowest layer, layer_index = 0.
	conf ['current_round'] [0] += 1

	last_epoch_loss = loss_list [-1]
	msg = dml_utils.log_loss (last_epoch_loss, conf ['current_round'] [0])
	worker_utils.send_print (ctl_addr, node_name + ': ' + msg)

	latest_weights = nn.model.get_weights ()
	send_self = dml_utils.send_weights (latest_weights, '/combine', conf ['father_node'] [:1],
		conf ['connect'], forward=conf ['forward'], layer=1)
	if send_self == 1:
		worker_utils.log ('send self at /combine')
		on_route_combine (latest_weights, 1)


@app.route ('/forward', methods=['POST'])
def route_forward ():
	print ('POST at /forward')
	node = request.form ['node']
	path = request.form ['path']
	worker_utils.log ('forward to ' + node + path)
	data = {'node': node, 'path': path, 'layer': request.form ['layer']}

	# exit the route_replace () will release the file weights.
	weights = io.BytesIO ()
	request.files.get ('weights').save (weights)
	weights.seek (0)

	executor.submit (on_route_forward, weights, data)
	return ''


def on_route_forward (weights, data):
	if data ['node'] in conf ['connect']:
		addr = conf ['connect'] [data ['node']]
		dml_utils.send_weights_helper (weights, data, addr, is_forward=False)
	else:
		addr = conf ['forward'] [data ['node']]
		dml_utils.send_weights_helper (weights, data, addr, is_forward=True)
	weights.seek (0)
	weights.truncate ()


app.run (host='0.0.0.0', port=dml_port, threaded=True)
