import os
import socket
import time

import requests
from flask import Flask, request

import util
from nns.nn_mnist import nn  # The only configurable parameter
from values import values_h

dirname = os.path.dirname (__file__)
port = os.getenv ('PORT')
if not port:
	port = '8888'
name = os.getenv ('NAME')
if not name:
	name = socket.gethostname ()

v = values_h.get_values (name)
nn.set_train_step (v ['learning_rate'])
nn.set_batch (v ['batch_size'], 1, v ['start_index'], v ['end_index'])
# nn.set_batch (10, 100, 0, 99)

start_time = time.time ()
util.train (1, nn.sess, nn.batch_size, nn.batch_num, nn.batch, nn.loss, nn.train_step, nn.xs, nn.ys)
total_time = time.time () - start_time
print ('time =', str (total_time))

file_path = os.path.abspath (os.path.join (dirname, 'master_ip.txt'))
with open (file_path, 'r') as f:
	master_ip = f.readline ().replace ('\n', '').replace ('\r', '')
	requests.get (
		'http://' + master_ip + ':9000/perf?host=' + name + '&time=' + str (total_time) + '&size=' + str (nn.size))

app = Flask (__name__)


# @app.route ('/hi', methods=['GET'])
# def hi ():
# 	loss = 0
# 	for i in range (nn.batch_num):
# 		batch_data = nn.sess.run (nn.batch)
# 		loss_val, _ = nn.sess.run ([nn.loss, nn.train_step], feed_dict={nn.xs: batch_data [0], nn.ys: batch_data [1]})
# 		loss += loss_val
# 	acc = nn.sess.run (nn.accuracy, feed_dict={nn.xs: nn.test_x, nn.ys: nn.test_y})
# 	return 'loss=' + str (loss) + ', acc=' + str (acc) + '\n'


@app.route ('/env', methods=['POST'])
def route_env ():
	file = request.files.get ('env')
	file.save (os.path.abspath (os.path.join (dirname, 'env/', file.filename)))
	exit ()


app.run (host='0.0.0.0', port=port, threaded=False)
