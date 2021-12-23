import io
import time

import numpy as np

import worker_utils

write = io.BytesIO ()
cur_index = 0


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


def train_all (model, images, labels, epochs, batch_size):
	h = model.fit (images, labels, epochs=epochs, batch_size=batch_size)
	return h.history ['loss']


def train (model, images, labels, epochs, batch_size, train_len):
	global cur_index
	cur_images = images [cur_index * 500: (cur_index + 1) * 500]
	cur_labels = labels [cur_index * 500: (cur_index + 1) * 500]
	cur_index += 1
	if cur_index == train_len:
		cur_index = 0
	h = model.fit (cur_images, cur_labels, epochs=epochs, batch_size=batch_size)
	return h.history ['loss']


def test (model, images, labels):
	loss, acc = model.test_on_batch (images, labels)
	return loss, acc


def test_on_batch (model, images, labels, batch_size):
	sample_number = images.shape [0]
	batch_number = sample_number // batch_size
	last = sample_number % batch_size
	total_loss, total_acc = 0.0, 0.0
	for i in range (batch_number):
		loss, acc = model.test_on_batch (images [i * batch_size:(i + 1) * batch_size],
			labels [i * batch_size:(i + 1) * batch_size])
		total_loss += loss * batch_size
		total_acc += acc * batch_size
	loss, acc = model.test_on_batch (images [batch_number * batch_size:],
		labels [batch_number * batch_size:])
	total_loss += loss * last
	total_acc += acc * last
	return total_loss / sample_number, total_acc / sample_number


def parse_weights (weights):
	w = np.load (weights, allow_pickle=True)
	return w


# only store the weights at received_weights [0]
# and accumulate as soon as new weights are received to save space :-)
def store_weights (received_weights, new_weights, received_count):
	if received_count == 1:
		received_weights.append (new_weights)
	else:
		received_weights [0] = np.add (received_weights [0], new_weights)


def avg_weights (received_weights, received_count):
	return np.divide (received_weights [0], received_count)


def assign_weights (model, weights):
	model.set_weights (weights)


def send_weights (weights, path, node_list, connect, forward=None, layer=-1):
	self = 0
	np.save (write, weights)
	write.seek (0)
	for node in node_list:
		if node == 'self':
			self = 1
			continue
		if node in connect:
			addr = connect [node]
			data = {'path': path, 'layer': str (layer)}
			send_weights_helper (write, data, addr, is_forward=False)
		elif forward:
			addr = forward [node]
			data = {'node': node, 'path': path, 'layer': str (layer)}
			send_weights_helper (write, data, addr, is_forward=True)
		else:
			Exception ('has not connect to ' + node)
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


def random_selection (node_list, number):
	return np.random.choice (node_list, number, replace=False)


def log_loss (loss, _round):
	"""
	we left a comma at the end for easy positioning and extending.
	this message can be parse by controller/ctl_utils.py, parse_log ().
	"""
	message = 'Train: loss={}, round={},'.format (loss, _round)
	worker_utils.log (message)
	return message


def log_acc (acc, _round, layer=-1):
	"""
	we left a comma at the end for easy positioning and extending.
	this message can be parsed by controller/ctl_utils.py, parse_log ().
	"""
	if layer != -1:
		message = 'Aggregate: accuracy={}, round={}, layer={},'.format (acc, _round, layer)
	else:
		message = 'Aggregate: accuracy={}, round={},'.format (acc, _round)
	worker_utils.log (message)
	return message
