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

input_shape = nn.input_shape
log_file = os.path.abspath (os.path.join (dirname, '../dml_file/log/', node_name + '.log'))
worker_utils.set_log (log_file)
conf = {}
# configurable parameter, specify the dataset path.
train_path = os.path.join (dirname, '../dataset/FASHION_MNIST/train_data')
train_images: np.ndarray
train_labels: np.ndarray
# configurable parameter, specify the dataset path.
test_path = os.path.join (dirname, '../dataset/FASHION_MNIST/test_data')
test_images: np.ndarray
test_labels: np.ndarray

app = Flask (__name__)
lock = threading.RLock ()
executor = ThreadPoolExecutor (1)

current_round: int = 0
current_step: int = 0
next_partition: int
temp_weights: list
temp_weights_flat: list  # a flattened view of temp_weights


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

	global train_images, train_labels
	train_images, train_labels = dml_utils.load_data (train_path, conf ['train_start_index'],
		conf ['train_len'], input_shape)
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

	conf ['current_round'] = 0
	return ''


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
	_, initial_acc = dml_utils.test_on_batch (nn.model, test_images, test_labels, conf ['batch_size'])
	msg = dml_utils.log_acc (initial_acc, 0)
	worker_utils.send_print (ctl_addr, node_name + ': ' + msg)
	on_route_train ()


@app.route ('/train', methods=['GET'])
def route_train ():
	print ('GET at /train')
	executor.submit (on_route_train)
	return ''


def on_route_train ():
	global current_round, temp_weights, temp_weights_flat, next_partition

	with lock:
		current_round += 1
		print (f'train, round {current_round}')
		loss_list = dml_utils.train (nn.model, train_images, train_labels,
			conf ['epoch'], conf ['batch_size'])
		last_epoch_loss = loss_list [-1]
		msg = dml_utils.log_loss (last_epoch_loss, current_round)
		worker_utils.send_print (ctl_addr, node_name + ': ' + msg)

		worker_utils.send_data ('POST', '/ok?name=' + node_name, ctl_addr)

		temp_weights = nn.model.get_weights ()
		temp_weights_flat = [layer_w.ravel () for layer_w in temp_weights]
		next_partition = conf ['pos']


@app.route ('/send', methods=['GET'])
def route_send_weights ():
	stage = request.args.get ('stage')
	step = request.args.get ('step')
	path = '/add' if stage == 'reduce' else '/update'
	executor.submit (on_route_send, path, int (step))
	return ''


def on_route_send (path: str, step: int):
	global next_partition

	# pos starts from 0
	partition = next_partition
	print (f'Node {node_name} - sending weights in round {current_round} to {path}, '
	       f'step {step}, pos {conf ["pos"]}, partition {partition}')

	weights_to_send = list ()
	for i in range (len (temp_weights_flat)):
		range_start = len (temp_weights_flat [i]) // conf ['ring_size'] * partition
		range_end = min (range_start + len (temp_weights_flat [i]) // conf ['ring_size'],
			len (temp_weights_flat [i]))
		weights_to_send.append (temp_weights_flat [i] [range_start:range_end])

	path = f'{path}?partition={partition}'
	dml_utils.send_weights (weights_to_send, path, [conf ['next_name']], conf ['connect'])
	next_partition = (next_partition + 1) % conf ['ring_size']


@app.route ('/add', methods=['POST'])
def route_add ():
	partition = request.args.get ('partition')
	print (f'POST at /add, round {current_round}, partition {partition}')
	received_weights = dml_utils.parse_weights (request.files.get ('weights'))
	executor.submit (on_route_add, int (partition), received_weights)
	return ''


def on_route_add (partition, weights):
	for i in range (len (temp_weights_flat)):
		range_start = len (temp_weights_flat [i]) // conf ['ring_size'] * partition
		range_end = min (range_start + len (temp_weights_flat [i]) // conf ['ring_size'],
			len (temp_weights_flat [i]))
		new_weights = np.add (temp_weights_flat [i] [range_start:range_end], weights [i])
		temp_weights_flat [i] [range_start:range_end] = new_weights

	worker_utils.send_data ('POST', '/ok?name=' + node_name, ctl_addr)


@app.route ('/update', methods=['POST'])
def route_update ():
	partition = request.args.get ('partition')
	print (f'POST at /update, round {current_round}, partition {partition}')
	received_weights = dml_utils.parse_weights (request.files.get ('weights'))
	executor.submit (on_route_update, int (partition), received_weights)
	return ''


def on_route_update (partition, weights):
	global current_step

	current_step += 1

	for i in range (len (temp_weights_flat)):
		range_start = len (temp_weights_flat [i]) // conf ['ring_size'] * partition
		range_end = min (range_start + len (temp_weights_flat [i]) // conf ['ring_size'],
			len (temp_weights_flat [i]))
		temp_weights_flat [i] [range_start:range_end] = weights [i]

	if current_step == conf ['ring_size'] - 1:
		current_step = 0

		with lock:
			weights = dml_utils.avg_weights ([np.array (temp_weights)], conf ['ring_size'])
			dml_utils.assign_weights (nn.model, weights)

			_, acc = dml_utils.test_on_batch (nn.model, test_images, test_labels, conf ['batch_size'])
			msg = dml_utils.log_acc (acc, current_round)
			worker_utils.send_print (ctl_addr, node_name + ': ' + msg)

		print ('Assign weights, round: %s, sync: %s' % (current_round, conf ['sync']))
		if current_round == conf ['sync']:
			worker_utils.send_data ('POST', 'finish?name=' + node_name, ctl_addr)
			return

	worker_utils.send_data ('POST', '/ok?name=' + node_name, ctl_addr)


app.run (host='0.0.0.0', port=dml_port, threaded=True)
