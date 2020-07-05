import io
import logging
import time

import math
import numpy as np
import requests
import tensorflow as tf

write = io.BytesIO ()


def set_log (hostname):
	logging.basicConfig (level=logging.INFO, filename='log/' + hostname + '.log', filemode='w', format='%(message)s')


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


def add_layer (assign_list, inputs, in_size, out_size, activation_function=None):
	w = tf.Variable (tf.random_normal ([in_size, out_size]))
	w_holder = tf.placeholder (tf.float32, [in_size, out_size])
	assign_list.append (tf.assign (w, w_holder))
	b = tf.Variable (tf.zeros ([1, out_size]) + 0.1)
	b_holder = tf.placeholder (tf.float32, [1, out_size])
	assign_list.append (tf.assign (b, b_holder))
	wx_plus_b = tf.matmul (inputs, w) + b
	if activation_function is None:
		outputs = wx_plus_b
	else:
		outputs = activation_function (wx_plus_b)
	return outputs


def train (local_epoch_num, batch_num, sess, batch, loss, train_step, xs, ys):
	loss_val = -1
	for epoch in range (local_epoch_num):
		for i in range (batch_num):
			batch_data = sess.run (batch)
			loss_val, _ = sess.run ([loss, train_step], feed_dict={xs: batch_data [0], ys: batch_data [1]})
	return loss_val


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


def send_weight_down_replace (w, addr_list, addr_bw, layer, is_binary=0):
	self = 0
	# w为file
	if is_binary == 1:
		for index in range (len (addr_list)):
			# 需要发给自己
			if addr_list [index] == 'self':
				self = 1
				continue
			file = {'weights': w}
			s_time = format (time.time (), '.1f')
			path = addr_list [index] + '/replace?layer=' + str (layer) \
			       + '&time=' + str (s_time) + '&bw=' + str (addr_bw [index])
			requests.post (path, files=file)
			w.seek (0)
		return self

	# w不为file，用write
	else:
		np.save (write, w)
		write.seek (0)
		for index in range (len (addr_list)):
			if addr_list [index] == 'self':
				self = 1
				continue
			file = {'weights': write}
			s_time = format (time.time (), '.1f')
			path = addr_list [index] + '/replace?layer=' + str (layer) \
			       + '&time=' + str (s_time) + '&bw=' + str (addr_bw [index])
			requests.post (path, files=file)
			write.seek (0)
		write.truncate ()
		return self


def send_weight_down_train (w, selected_index, addr_list, addr_bw, is_binary=0):
	self = 0
	if is_binary == 1:
		for i in selected_index:
			if addr_list [i] == 'self':
				self = 1
				continue
			file = {'weights': w}
			s_time = format (time.time (), '.1f')
			path = addr_list [i] + '/train?time=' + str (s_time) + '&bw=' + str (addr_bw [i])
			requests.post (path, files=file)
			w.seek (0)
		return self

	else:
		np.save (write, w)
		write.seek (0)
		for i in selected_index:
			if addr_list [i] == 'self':
				self = 1
				continue
			file = {'weights': write}
			s_time = format (time.time (), '.1f')
			path = addr_list [i] + '/train?time=' + str (s_time) + '&bw=' + str (addr_bw [i])
			requests.post (path, files=file)
			write.seek (0)
		write.truncate ()
		return self


def send_weight_up_combine (w, addr, bw, layer):
	if addr == 'self':
		return 1
	np.save (write, w)
	write.seek (0)
	file = {'weights': write}
	s_time = format (time.time (), '.1f')
	path = addr + '/combine?layer=' + str (layer) + '&time=' \
	       + str (s_time) + '&bw=' + str (bw)
	requests.post (path, files=file)
	write.seek (0)
	write.truncate ()
	return 0


def index_random (worker_num, fraction):
	return np.random.choice (worker_num, int (math.ceil (float (worker_num) * fraction)), replace=False)


def index_full (length):
	return range (length)
