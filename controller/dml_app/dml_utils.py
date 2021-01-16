import io
import time

import numpy as np

import worker_utils

write = io.BytesIO ()


def load_data (path, start_index, _len, input_shape):
	x_list = []
	y_list = []
	for i in range (_len):
		x_list.append (np.load (path + '/images_' + str (start_index + i) + '.npy')
			.reshape (input_shape))
		y_list.append (np.load (path + '/labels_' + str (start_index + i) + '.npy'))
	images = np.concatenate (tuple (x_list))
	labels = np.concatenate (tuple (y_list))
	return images, labels


def send_perf (ctl_address: str, name: str, t_time: float, size: int):
	if ctl_address:
		path = '/perf?node=' + name + '&time=' + str (t_time) + '&size=' + str (size)
		worker_utils.send_data ('GET', path, ctl_address)


def parse_weights (weights):
	w = np.load (weights, allow_pickle=True)
	return w


# only store the weights at received_weights[layer_index][0]
# and accumulate as soon as new parameters are received.
def store_weights (new_weights, received_weights, received_count):
	if received_count == 1:
		received_weights.append (new_weights)
	else:
		received_weights [0] = np.add (received_weights [0], new_weights)


def avg_weights (received_weights, received_count):
	return received_weights [0] / received_count


def assign_weights (model, weights):
	model.set_weights (weights)


def send_weights (weights, index, node_list, connect, forward, path, layer=2):
	self = 0
	np.save (write, weights)
	write.seek (0)
	for i in index:
		if node_list [i] == 'self':
			self = 1
			continue
		if node_list [i] in connect:
			addr = connect [node_list [i]]
			data = {'path': path, 'layer': str (layer)}
			send_weights_helper (write, data, addr, is_forward=False)
		else:
			addr = forward [node_list [i]]
			data = {'node': node_list [i], 'path': path, 'layer': str (layer)}
			send_weights_helper (write, data, addr, is_forward=True)
		write.seek (0)
	write.truncate ()
	return self


def send_weights_helper (weights, data, addr, is_forward):
	s = time.time ()
	if not is_forward:
		worker_utils.send_data ('POST', data ['path'], addr, data=data, files={'weights': weights})
	else:
		worker_utils.log ('need ' + addr + ' to forward to ' + data ['node'] + data ['path'])
		worker_utils.send_data ('POST', '/forward', addr, data=data, files={'weights': weights})
	e = time.time ()
	worker_utils.log ('send weights to ' + addr + ', cost=' + str (e - s))


def index_random (worker_num, fraction):
	return np.random.choice (worker_num, int (float (worker_num) * fraction),
		replace=False)


def index_full (length):
	return range (length)


def log_loss (loss: float, _round: int):
	"""
	we left a comma at the end for easy positioning and extending.
	this message can be parse by controller/ctl_utils.py, parse_log ().
	"""
	message = 'Train: loss={}, round={},'.format (loss, _round)
	worker_utils.log (message)
	return message


def log_acc (acc: float, _round: int, layer: int = -1):
	"""
	we left a comma at the end for easy positioning and extending.
	this message can be parsed by controller/ctl_utils.py, parse_log ().
	"""
	message = 'Aggregate: accuracy={}, round={}, layer={},'.format (acc, _round, layer)
	worker_utils.log (message)
	return message
