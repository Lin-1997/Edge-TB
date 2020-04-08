import tensorflow as tf
import numpy as np
import io
import logging
import requests


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


def save_received_weight (current_w, new_w):
	current_w.append (np.load (new_w, allow_pickle=True))


def calculate_avg_weight (received_w, received_count):
	# 先存下第0个client的参数|W|，顺便初始化格式
	total_w = received_w [0]
	for w_index in range (1, len (received_w)):
		tmp_w = []
		# 依次取出从1开始的client的参数|W|
		one_weight = received_w [w_index]
		# |w0, w1...|逐位累加
		for i in range (len (total_w)):
			tmp_w.append (np.sum ([total_w [i], one_weight [i]], axis=0))
		total_w = tmp_w
	# total_w = |w0_sum, w1_sum...|

	# 计算每位的平均参数
	avg_w = [each_w / received_count for each_w in total_w]
	# avg_w = |w0_avg, w1_avg...|
	return avg_w


def assignment (assign_list, avg_w, sess):
	# 把接收到的权重赋值给当前网络
	weight_placeholder_start_index = 2
	# assign_list = [tf.assign (weights, weight_holder), tf.assign (biases, biases_holder)...]
	# 指向网络中所有权重的指针，通过weight_assign_op_list可以直接向网络的权重赋值
	for w, r in zip (assign_list, avg_w):
		sess.run (w, feed_dict={"Placeholder_" + str (weight_placeholder_start_index) + ":0": r})
		weight_placeholder_start_index += 1


def send_weight (w, client_list, addr):
	# 向下一轮节点发送整合后的参数
	write = io.BytesIO ()
	np.save (write, w, allow_pickle=True)
	write.seek (0)
	file = {'central_weights': write}

	# 向选好的节点发送数据
	for i in client_list:
		logging.info ("client_{} selected".format (i))
		requests.post (
			"http://localhost:" + str (addr [i]) + "/update_weights_then_training",
			files=file)
		write.seek (0)
		file = {'central_weights': write}


def client_list_random (client_num, fraction):
	return np.random.choice (client_num, int (client_num * fraction), replace=False)
