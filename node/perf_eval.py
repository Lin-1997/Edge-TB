import os
import socket
import time

import requests
from flask import Flask, request

import util
from nns.nn_cifar import nn
from values import values_h

dirname = os.path.dirname (__file__)
port = os.getenv ('PORT')
if not port:
	port = '8888'
name = os.getenv ('NAME')
if not name:
	name = socket.gethostname ()

v = values_h.get_values (name)
nn.set_train_lr (v ['learning_rate'])
nn.set_train_data_batch (v ['batch_size'], 1, v ['start_index'], v ['end_index'])

start_time = time.process_time ()
util.train (1, nn.batch_num, nn.sess, nn.batch, nn.loss, nn.train_step, nn.xs, nn.ys)
total_time = time.process_time () - start_time
print ('time=', str (total_time))

file_path = os.path.abspath (os.path.join (dirname, 'master_ip.txt'))
with open (file_path, 'r') as f:
	master_ip = f.readline ().replace ('\n', '').replace ('\r', '')
	requests.get (
		'http://' + master_ip + ':9000/perf?host=' + name + '&time=' + str (total_time) + '&size=' + str (nn.size))

app = Flask (__name__)


@app.route ('/env', methods=['POST'])
def route_env ():
	file = request.files.get ('env')
	file.save (os.path.abspath (os.path.join (dirname, 'env/', file.filename)))
	exit ()


app.run (host='0.0.0.0', port=port, threaded=False)
