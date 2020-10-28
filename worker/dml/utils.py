import io
import time

import numpy as np
import requests

from worker_utils import log

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


def send_weights (weights, selected_index, host_list, node_map,
		forward_map, path, layer=2):
	self = 0
	np.save (write, weights)
	write.seek (0)
	for index in selected_index:
		if host_list [index] == 'self':
			self = 1
			continue
		if host_list [index] in node_map:
			addr = node_map [host_list [index]]
			data = {'path': path, 'layer': str (layer)}
			send (write, data, addr, is_forward=False)
		else:
			addr = forward_map [host_list [index]]
			data = {'host': host_list [index], 'path': path, 'layer': str (layer)}
			send (write, data, addr, is_forward=True)
		write.seek (0)
	write.truncate ()
	return self


def send (weights, data, addr, is_forward):
	s = time.time ()
	if not is_forward:
		requests.post (addr + data ['path'], data=data, files={'weights': weights})
	else:
		requests.post (addr + '/forward', data=data, files={'weights': weights})
	e = time.time ()
	log ('send weights to ' + addr + ', s=' + str (s) + ', e=' + str (e) + ', cost=' + str (e - s))


def send_message (ctl_addr, path, name):
	try:
		requests.get ('http://' + ctl_addr + path + '?host=' + name)
	except requests.exceptions.ConnectionError:
		pass


def index_random (worker_num, fraction):
	return np.random.choice (worker_num, int (float (worker_num) * fraction),
		replace=False)


def index_full (length):
	return range (length)
