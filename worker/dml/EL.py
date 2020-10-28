import io
import os
import socket
import threading
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request

import utils
import worker_utils
from nns.nn_mnist import nn  # configurable parameter, from nns.whatever import nn
from values import values_h

dirname = os.path.abspath (os.path.dirname (__file__))
port = os.getenv ('PORT')
if not port:
	port = '8888'
name = os.getenv ('NAME')
if not name:
	name = socket.gethostname ()
net_ctl_address = os.getenv ('NET_CTL_ADDRESS')

model = nn.model
input_shape = nn.input_shape
filename = worker_utils.set_log (name)
v = values_h.get_values (name)

if 'train_len' in v and v ['train_len'] > 0:
	# configurable parameter, specify the dataset path
	train_path = os.path.join (dirname, 'datasets/MNIST/train_data')
	train_images, train_labels = utils.load_data (train_path, v ['train_start_i'],
		v ['train_len'], input_shape)
if 'test_len' in v and v ['test_len'] > 0:
	# configurable parameter, specify the dataset path
	test_path = os.path.join (dirname, 'datasets/MNIST/test_data')
	test_images, test_labels = utils.load_data (test_path, v ['test_start_i'],
		v ['test_len'], input_shape)
utils.send_message (net_ctl_address, '/ready', name)

app = Flask (__name__)
weights_lock = threading.Lock ()
executor = ThreadPoolExecutor (1)


@app.route ('/hi', methods=['GET'])
def route_hi ():
	return 'this is node ' + name + '\n'


@app.route ('/log', methods=['GET'])
def route_log ():
	worker_utils.send_log (filename, name)
	return ''


@app.route ('/start', methods=['GET'])
def route_start ():
	initial_weights = model.get_weights ()
	_type = request.args.get ('type', default=0, type=int)
	initial_acc = model.test_on_batch (test_images, test_labels) [1]
	executor.submit (on_route_start, initial_weights, _type)
	return str (initial_acc)


def on_route_start (initial_weights, _type):
	# EL
	if _type == 0:
		self_layer = v ['layer'] [-1]
		i_full = utils.index_full (v ['down_count'] [-1])
		if self_layer != 2:
			send_self = utils.send_weights (initial_weights, i_full, v ['down_host'] [-1],
				v ['node'], v ['forward'], '/replace', layer=self_layer)
			if send_self == 1:
				on_route_replace (initial_weights, self_layer)
		else:
			send_self = utils.send_weights (initial_weights, i_full, v ['down_host'] [-1],
				v ['node'], v ['forward'], '/train')
			if send_self == 1:
				on_route_train (initial_weights)
		worker_utils.send_print ('start EL')
	# FL.
	elif _type == 1:
		i_random = utils.index_random (v ['down_count'] [0], v ['worker_fraction'])
		utils.send_weights (initial_weights, i_random, v ['down_host'] [0],
			v ['node'], v ['forward'], '/train')
		worker_utils.send_print ('start FL')
	# TODO GL.
	elif _type == 2:
		worker_utils.send_print ('start GL')
	else:
		worker_utils.send_print ('error at start')


# replace request from the upper layer node.
@app.route ('/replace', methods=['POST'])
def route_replace ():
	file_weights = request.files.get ('weights')
	from_layer = request.form.get ('layer', type=int)
	weights = utils.parse_weights (file_weights)
	executor.submit (on_route_replace, weights, from_layer)
	return ''


def on_route_replace (weights, from_layer):
	self_layer = from_layer - 1
	layer_index = v ['layer'].index (self_layer)
	i_full = utils.index_full (v ['down_count'] [layer_index])

	# 2nd layer of EL, lower layer nodes are trainers, path=train.
	if self_layer == 2:
		send_self = utils.send_weights (weights, i_full, v ['down_host'] [layer_index],
			v ['node'], v ['forward'], '/train')
		if send_self == 1:
			on_route_train (weights)

	# middle layer of EL, lower layer nodes are aggregators, path=replace.
	else:
		send_self = utils.send_weights (weights, i_full, v ['down_host'] [layer_index],
			v ['node'], v ['forward'], '/replace', layer=self_layer)
		if send_self == 1:
			on_route_replace (weights, self_layer)


# combine request from the lower layer node.
@app.route ('/combine', methods=['POST'])
def route_combine ():
	file_weights = request.files.get ('weights')
	from_layer = request.form.get ('layer', type=int)
	weights = utils.parse_weights (file_weights)
	executor.submit (on_route_combine, weights, from_layer)
	return ''


def on_route_combine (weights, from_layer):
	self_layer = from_layer + 1
	layer_index = v ['layer'].index (self_layer)

	weights_lock.acquire ()
	v ['received_count'] [layer_index] += 1
	utils.store_weights (weights, v ['received_weights'] [layer_index],
		v ['received_count'] [layer_index])
	weights_lock.release ()

	if v ['received_count'] [layer_index] == \
			int (v ['down_count'] [layer_index] * v ['worker_fraction']):
		combine_weights (layer_index)


def combine_weights (layer_index):
	weights = utils.avg_weights (v ['received_weights'] [layer_index],
		v ['received_count'] [layer_index])
	utils.assign_weights (model, weights)
	v ['received_weights'] [layer_index].clear ()
	v ['received_count'] [layer_index] = 0
	v ['current_round'] [layer_index] += 1

	acc = model.test_on_batch (test_images, test_labels) [1]
	_round, layer = v ['current_round'] [layer_index], v ['layer'] [layer_index]
	msg = worker_utils.log_acc (acc, _round, layer)
	worker_utils.send_print (name + ': ' + msg)

	# EL.
	if v ['type'] == 0:
		self_layer = v ['layer'] [layer_index]
		# meet the sync of this layer, send up to combine.
		if v ['current_round'] [layer_index] % v ['sync'] [layer_index] == 0:
			# is the top node.
			if v ['up_host'] [layer_index] == 'top':
				worker_utils.log ('>>>>>training ended<<<<<')
				utils.send_message (net_ctl_address, '/finish', name)
			# isn't the top node.
			else:
				send_self = utils.send_weights (weights, [layer_index], v ['up_host'],
					v ['node'], v ['forward'], '/combine', layer=self_layer)
				if send_self == 1:
					on_route_combine (weights, self_layer)

		# haven't meet the sync, send down.
		else:
			i_full = utils.index_full (v ['down_count'] [layer_index])
			# path=train.
			if self_layer == 2:
				send_self = utils.send_weights (weights, i_full, v ['down_host'] [layer_index],
					v ['node'], v ['forward'], '/train')
				if send_self == 1:
					on_route_train (weights)
			# path=replace.
			else:
				send_self = utils.send_weights (weights, i_full, v ['down_host'] [layer_index],
					v ['node'], v ['forward'], '/replace', layer=self_layer)
				if send_self == 1:
					on_route_replace (weights, self_layer)

	# FL
	else:
		# end.
		if v ['current_round'] [layer_index] == v ['sync'] [0]:
			worker_utils.log ('>>>>>training ended<<<<<')
			utils.send_message (net_ctl_address, '/finish', name)
		# send down to train.
		else:
			i_random = utils.index_random (v ['down_count'] [0], v ['worker_fraction'])
			utils.send_weights (weights, i_random, v ['down_host'] [0],
				v ['node'], v ['forward'], '/train')


# train request from the upper layer node.
@app.route ('/train', methods=['POST'])
def route_train ():
	file_weights = request.files.get ('weights')
	weights = utils.parse_weights (file_weights)
	executor.submit (on_route_train, weights)
	return ''


def on_route_train (received_weights):
	utils.assign_weights (model, received_weights)
	h = model.fit (train_images, train_labels, epochs=v ['local_epoch_num'],
		batch_size=v ['batch_size'])
	# must be the lowest layer.
	v ['current_round'] [0] += 1

	last_epoch_loss = h.history ['loss'] [-1]
	msg = worker_utils.log_loss (last_epoch_loss, v ['current_round'] [0])
	worker_utils.send_print (name + ': ' + msg)

	latest_weights = model.get_weights ()
	send_self = utils.send_weights (latest_weights, [0], v ['up_host'],
		v ['node'], v ['forward'], '/combine', layer=1)
	if send_self == 1:
		on_route_combine (latest_weights, 1)


@app.route ('/forward', methods=['POST'])
def route_forward ():
	file_weights = request.files.get ('weights')
	data = {'host': request.form ['host'], 'path': request.form ['path'],
	        'layer': request.form ['layer']}

	# exit the route_replace () will release the file_weights.
	weights = io.BytesIO ()
	file_weights.save (weights)
	weights.seek (0)

	executor.submit (on_route_forward, weights, data)
	return ''


def on_route_forward (weights, data):
	if data ['host'] in v ['node']:
		addr = v ['node'] [data ['host']]
		utils.send (weights, data, addr, is_forward=False)
	else:
		addr = v ['forward'] [data ['host']]
		utils.send (weights, data, addr, is_forward=True)
	weights.seek (0)
	weights.truncate ()


app.run (host='0.0.0.0', port=port, threaded=True)
