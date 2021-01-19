import io
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request
from numpy import ndarray

import dml_utils
import worker_utils
from nns.nn_mnist import nn  # configurable parameter, from nns.whatever import nn.
from values import values_h

dirname = os.path.abspath (os.path.dirname (__file__))

# listen on port 4444.
# we do not recommend changing this port number, but if you really want to change it,
# you need to change controller/ctl_run_example.py, controller/dml_app/dml_listener.py,
# controller/class_node.py, controller/dml_tool/conf_generator.py together.
dml_port = 4444

ctl_addr = os.getenv ('NET_CTL_ADDRESS')
agent_addr = os.getenv ('NET_AGENT_ADDRESS')
node_name = os.getenv ('NET_NODE_NAME')

model = nn.model
initial_weights = model.get_weights ()
input_shape = nn.input_shape
log_file = os.path.abspath (os.path.join (dirname, '../dml_file/log/',
	node_name + '.log'))
worker_utils.set_log (log_file)
v = {}
# configurable parameter, specify the dataset path.
test_path = os.path.join (dirname, 'datasets/MNIST/test_data')
test_images: ndarray
test_labels: ndarray
# configurable parameter, specify the dataset path.
train_path = os.path.join (dirname, 'datasets/MNIST/train_data')
train_images: ndarray
train_labels: ndarray

app = Flask (__name__)
weights_lock = threading.Lock ()
executor = ThreadPoolExecutor (1)


# if this is container, docker will send a GET to here every 30s
# this ability is defined in controller/class_node.py, ContainerServer.save_yml (), healthcheck.
@app.route ('/hi', methods=['GET'])
def route_hi ():
	# send a heartbeat to the agent.
	# when the agent receives the heartbeat of a container for the first time,
	# it will deploy the container's tc settings.
	# please ensure that your app implements this function, i.e.,
	# receiving docker healthcheck and sending heartbeat to the agent.
	worker_utils.heartbeat (agent_addr, node_name)
	return 'this is node ' + node_name + '\n'


@app.route ('/conf', methods=['POST'])
def route_conf ():
	global v, test_images, test_labels, train_images, train_labels
	filename = os.path.join (dirname, '../dml_file/conf', node_name + '.conf')
	request.files.get ('conf').save (filename)
	if v:
		v.update (values_h.get_values (node_name))
	else:
		v.update (values_h.get_values (node_name))
		if 'test_len' in v and v ['test_len'] > 0:
			test_images, test_labels = dml_utils.load_data (test_path, v ['test_start_i'],
				v ['test_len'], input_shape)
		if 'train_len' in v and v ['train_len'] > 0:
			train_images, train_labels = dml_utils.load_data (train_path, v ['train_start_i'],
				v ['train_len'], input_shape)
		executor.submit (perf_eval)
	return ''


# performance evaluation for trainer.
def perf_eval ():
	if 'train_len' in v and v ['train_len'] > 0:
		s_time = time.time ()
		model.fit (train_images, train_labels, epochs=1, batch_size=v ['batch_size'])
		t_time = time.time () - s_time
	else:
		t_time = -1.0  # not trainer.
	dml_utils.send_perf (ctl_addr, node_name, t_time, nn.size)
	worker_utils.log (node_name + ': 1 epoch time=' + str (t_time))


@app.route ('/log', methods=['GET'])
def route_log ():
	executor.submit (on_route_log)
	return ''


def on_route_log ():
	worker_utils.send_log (ctl_addr, log_file, node_name)


@app.route ('/start', methods=['GET'])
def route_start ():
	_type = request.args.get ('type', type=int, default=0)
	initial_acc = model.test_on_batch (test_images, test_labels) [1]
	executor.submit (on_route_start, _type)
	return str (initial_acc)


def on_route_start (_type):
	# EL
	if _type == 0:
		self_layer = v ['layer'] [-1]
		i_full = dml_utils.index_full (len (v ['down_node'] [-1]))
		if self_layer != 2:
			send_self = dml_utils.send_weights (initial_weights, i_full, v ['down_node'] [-1],
				v ['connect'], v ['forward'], '/replace', layer=self_layer)
			if send_self == 1:
				worker_utils.log ('send self at /replace')
				on_route_replace (initial_weights, self_layer)
		else:
			send_self = dml_utils.send_weights (initial_weights, i_full, v ['down_node'] [-1],
				v ['connect'], v ['forward'], '/train')
			if send_self == 1:
				worker_utils.log ('send self at /train')
				on_route_train (initial_weights)
		worker_utils.send_print (ctl_addr, 'start EL')
	# FL.
	elif _type == 1:
		i_random = dml_utils.index_random (len (v ['down_node'] [0]), v ['worker_fraction'])
		dml_utils.send_weights (initial_weights, i_random, v ['down_node'] [0],
			v ['connect'], v ['forward'], '/train')
		worker_utils.send_print (ctl_addr, 'start FL')
	else:
		worker_utils.send_print (ctl_addr, 'error at start')


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
	layer_index = v ['layer'].index (self_layer)
	i_full = dml_utils.index_full (len (v ['down_node'] [layer_index]))

	# 2nd layer of EL, lower layer nodes are trainers, path=train.
	if self_layer == 2:
		send_self = dml_utils.send_weights (weights, i_full, v ['down_node'] [layer_index],
			v ['connect'], v ['forward'], '/train')
		if send_self == 1:
			worker_utils.log ('send self at /train')
			on_route_train (weights)

	# middle layer of EL, lower layer nodes are aggregators, path=replace.
	else:
		send_self = dml_utils.send_weights (weights, i_full, v ['down_node'] [layer_index],
			v ['connect'], v ['forward'], '/replace', layer=self_layer)
		if send_self == 1:
			worker_utils.log ('send self at /replace')
			on_route_replace (weights, self_layer)


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
	layer_index = v ['layer'].index (self_layer)

	weights_lock.acquire ()
	v ['received_number'] [layer_index] += 1
	dml_utils.store_weights (weights, v ['received_weights'] [layer_index],
		v ['received_number'] [layer_index])
	weights_lock.release ()

	if v ['received_number'] [layer_index] == \
			int (len (v ['down_node'] [layer_index]) * v ['worker_fraction']):
		combine_weights (layer_index)


def combine_weights (layer_index):
	weights = dml_utils.avg_weights (v ['received_weights'] [layer_index],
		v ['received_number'] [layer_index])
	dml_utils.assign_weights (model, weights)
	v ['received_weights'] [layer_index].clear ()
	v ['received_number'] [layer_index] = 0
	v ['current_round'] [layer_index] += 1

	acc = model.test_on_batch (test_images, test_labels) [1]
	_round, layer = v ['current_round'] [layer_index], v ['layer'] [layer_index]
	msg = dml_utils.log_acc (acc, _round, layer)
	worker_utils.send_print (ctl_addr, node_name + ': ' + msg)

	# EL.
	if v ['type'] == 0:
		self_layer = v ['layer'] [layer_index]
		# meet the sync of this layer, send up to combine.
		if v ['current_round'] [layer_index] % v ['sync'] [layer_index] == 0:
			# is the top node.
			if v ['up_node'] [layer_index] == 'top':
				worker_utils.log ('>>>>>training ended<<<<<')
				worker_utils.send_data ('GET', '/finish', ctl_addr)
			# isn't the top node.
			else:
				send_self = dml_utils.send_weights (weights, [layer_index], v ['up_node'],
					v ['connect'], v ['forward'], '/combine', layer=self_layer)
				if send_self == 1:
					worker_utils.log ('send self at /combine')
					on_route_combine (weights, self_layer)

		# haven't meet the sync, send down.
		else:
			i_full = dml_utils.index_full (len (v ['down_node'] [layer_index]))
			# path=train.
			if self_layer == 2:
				send_self = dml_utils.send_weights (weights, i_full, v ['down_node'] [layer_index],
					v ['connect'], v ['forward'], '/train')
				if send_self == 1:
					worker_utils.log ('send self at /train')
					on_route_train (weights)
			# path=replace.
			else:
				send_self = dml_utils.send_weights (weights, i_full, v ['down_node'] [layer_index],
					v ['connect'], v ['forward'], '/replace', layer=self_layer)
				if send_self == 1:
					worker_utils.log ('send self at /replace')
					on_route_replace (weights, self_layer)

	# FL
	else:
		# end.
		if v ['current_round'] [layer_index] == v ['sync'] [0]:
			worker_utils.log ('>>>>>training ended<<<<<')
			worker_utils.send_data ('GET', '/finish', ctl_addr)
		# send down to train.
		else:
			i_random = dml_utils.index_random (len (v ['down_node'] [0]), v ['worker_fraction'])
			dml_utils.send_weights (weights, i_random, v ['down_node'] [0],
				v ['connect'], v ['forward'], '/train')


# train request from the upper layer node.
@app.route ('/train', methods=['POST'])
def route_train ():
	print ('POST at /train')
	weights = dml_utils.parse_weights (request.files.get ('weights'))
	executor.submit (on_route_train, weights)
	return ''


def on_route_train (received_weights):
	dml_utils.assign_weights (model, received_weights)
	h = model.fit (train_images, train_labels, epochs=v ['epoch'], batch_size=v ['batch_size'])
	# must be the lowest layer.
	v ['current_round'] [0] += 1

	last_epoch_loss = h.history ['loss'] [-1]
	msg = dml_utils.log_loss (last_epoch_loss, v ['current_round'] [0])
	worker_utils.send_print (ctl_addr, node_name + ': ' + msg)

	latest_weights = model.get_weights ()
	send_self = dml_utils.send_weights (latest_weights, [0], v ['up_node'],
		v ['connect'], v ['forward'], '/combine', layer=1)
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
	if data ['node'] in v ['connect']:
		addr = v ['connect'] [data ['node']]
		dml_utils.send_weights_helper (weights, data, addr, is_forward=False)
	else:
		addr = v ['forward'] [data ['node']]
		dml_utils.send_weights_helper (weights, data, addr, is_forward=True)
	weights.seek (0)
	weights.truncate ()


app.run (host='0.0.0.0', port=dml_port, threaded=True)
