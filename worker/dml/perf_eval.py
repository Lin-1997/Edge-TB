import os
import socket
import time

import requests
from flask import Flask, request

import utils
from nns.nn_mnist import nn  # configurable parameter, from nns.whatever import nn
from values import values_h

dirname = os.path.dirname (__file__)
port = os.getenv ('PORT')
if not port:
	port = '8888'
name = os.getenv ('NAME')
if not name:
	name = socket.gethostname ()
net_ctl_address = os.getenv ('NET_CTL_ADDRESS')

model = nn.model
size = nn.size
input_shape = nn.input_shape
v = values_h.get_values (name)
if 'train_len' in v and v ['train_len'] > 0:
	# configurable parameter, specify the dataset path
	train_path = os.path.abspath (os.path.join (dirname, 'datasets/MNIST/train_data'))
	train_images, train_labels = utils.load_data (train_path, v ['train_start_i'], v ['train_len'], input_shape)
	s_time = time.time ()
	model.fit (train_images, train_labels, epochs=1, batch_size=v ['batch_size'])
	t_time = time.time () - s_time
else:
	t_time = -1.0

requests.get ('http://' + net_ctl_address + '/perf?host=' + name + '&time=' + str (t_time) + '&size=' + str (size))

app = Flask (__name__)


@app.route ('/env', methods=['POST'])
def route_env ():
	file = request.files.get ('env')
	file.save (os.path.abspath (os.path.join (dirname, 'env/', file.filename)))
	exit ()


app.run (host='0.0.0.0', port=port, threaded=False)
