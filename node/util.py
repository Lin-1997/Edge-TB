import io
import logging
import os
import time

import numpy as np
import requests

write = io.BytesIO ()
dirname = os.path.dirname (__file__)


def set_log (name):
	filename = os.path.abspath (os.path.join (dirname, 'log/', name + '.log'))
	logging.basicConfig (level=logging.INFO, filename=filename, filemode='w', format='%(message)s')


def log (message):
	logging.info (message)


def calculate_size (w):
	np.save (write, w)
	write.seek (0)
	size = len (write.read ())
	write.seek (0)
	write.truncate ()
	return size


def simulate_sleep (size, s_time, bw):
	n_time = float (format (size / bw, '.1f'))
	c_time = time.time ()
	t = s_time + n_time - c_time
	if t > 0.2:
		time.sleep (t)


def train (local_epoch_num, sess, batch_num, batch, loss, train_step, xs, ys):
	total_loss = 0
	for epoch in range (local_epoch_num):
		for i in range (batch_num):
			batch_data = sess.run (batch)
			loss_val, _ = sess.run ([loss, train_step], feed_dict={xs: batch_data [0], ys: batch_data [1]})
			total_loss += loss_val
	return total_loss


def parse_received_weight (new_w):
	return np.load (new_w, allow_pickle=True)


def calculate_avg_weight (received_w, received_count):
	# 先存下第0个worker的参数|W|，顺便初始化格式
	total_w = received_w [0]
	for w_index in range (1, received_count):
		tmp_w = []
		# 依次取出从1开始的worker的参数|W|
		w = received_w [w_index]
		# |w0, w1...|逐位累加
		for i in range (len (total_w)):
			tmp_w.append (np.sum ([total_w [i], w [i]], axis=0))
		total_w = tmp_w
	# total_w = |w0_sum, w1_sum...|

	# 计算每位的平均参数
	avg_w = [each_w / received_count for each_w in total_w]
	# avg_w = |w0_avg, w1_avg...|
	return avg_w


def assignment (assign_list, w, sess):
	# 把接收到的权重赋值给当前网络
	weight_placeholder_start_index = 2
	# assign_list = [tf.assign (weights, weight_holder), tf.assign (biases, biases_holder)...]
	# 指向网络中所有权重的指针，通过weight_assign_op_list可以直接向网络的权重赋值
	for w, r in zip (assign_list, w):
		sess.run (w, feed_dict={"Placeholder_" + str (weight_placeholder_start_index) + ":0": r})
		weight_placeholder_start_index += 1


def send_weight (weights, selected_index, host_list, node_map, forward_map, bw_map, path, layer=2, is_binary=0):
	self = 0
	# w为file
	if is_binary == 1:
		for index in selected_index:
			# 需要发给自己
			if host_list [index] == 'self':
				self = 1
				continue
			if host_list [index] in node_map:
				addr = node_map [host_list [index]]
				data = {'path': path, 'layer': str (layer)}
				send (weights, data, addr, bw_map [addr], is_forward=False)
			else:
				addr = forward_map [host_list [index]]
				data = {'host': host_list [index], 'path': path, 'layer': str (layer)}
				send (weights, data, addr, bw_map [addr], is_forward=True)
			weights.seek (0)
		return self

	# w不为file，用write
	else:
		np.save (write, weights)
		write.seek (0)
		for index in selected_index:
			if host_list [index] == 'self':
				self = 1
				continue
			if host_list [index] in node_map:
				addr = node_map [host_list [index]]
				data = {'path': path, 'layer': str (layer)}
				send (write, data, addr, bw_map [addr], is_forward=False)
			else:
				addr = forward_map [host_list [index]]
				data = {'host': host_list [index], 'path': path, 'layer': str (layer)}
				send (write, data, addr, bw_map [addr], is_forward=True)
			write.seek (0)
		write.truncate ()
		return self


def send (weights, data, addr, bw, is_forward):
	file = {'weights': weights}
	s_time = format (time.time (), '.1f')
	data.update ({'time': str (s_time), 'bw': str (bw)})
	if not is_forward:
		requests.post (addr + data ['path'], data=data, files=file)
	else:
		requests.post (addr + '/forward', data=data, files=file)


def send_message (master_ip, path):
	requests.get ('http://' + master_ip + ':9000/' + path)


def send_print (master_ip, msg):
	requests.post ('http://' + master_ip + ':9000/print', data={'msg': msg})


def send_log (master_ip, name):
	file_path = os.path.abspath (os.path.join (dirname, 'log/', name + '.log'))
	with open (file_path, 'r') as f:
		requests.post ('http://' + master_ip + ':9000/log', files={'log': f})


def index_random (worker_num, fraction):
	return np.random.choice (worker_num, int (float (worker_num) * fraction), replace=False)


def index_full (length):
	return range (length)
