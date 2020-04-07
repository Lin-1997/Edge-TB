import numpy as np
import requests
import getopt
import sys
import logging
import tensorflow as tf
import io
import threading
from flask import Flask, request
from concurrent.futures import ThreadPoolExecutor

import util

config = tf.ConfigProto ()
# config.gpu_options.allow_growth = True

client_num = 2
fraction_each_round = 0.5
start_port = 9990
communication_round_time = 40
all_addresses = []
weight_assign_op_list = []

logging.basicConfig (level=logging.INFO, filename='log/parameter_server.log', filemode='w',
                     format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')

lock = threading.Lock ()

try:
	options, args = getopt.getopt (sys.argv [1:], "n:c:r:", ["client_num=", "fraction=", "communication_round_time="])
except getopt.GetoptError:
	sys.exit ()

for option, value in options:
	if option in ("-n", "--client_num"):
		client_num = int (value)
	if option in ("-c", "--fraction"):
		fraction_each_round = float (value)
	if option in ("-r", "--communication_round_time"):
		communication_round_time = int (value)
if len (args) > 0:
	print ("error args: {0}".format (args))

for client_index in range (client_num):
	all_addresses.append (start_port + client_index)

# ===================================================
# 与网络对应的数据
# 应该和网络一起放到nn_load.nn_xx中

# make up some real data
test_x = np.array (
	[-0.99, -0.89, -0.79, -0.69, -0.59, -0.49, -0.39, -0.29, -0.19, -0.09, 0.09, 0.19, 0.29, 0.39, 0.49, 0.59,
	 0.69, 0.79, 0.89, 0.99]) [:, np.newaxis]
noise = np.random.normal (0, 0.05, test_x.shape).astype (np.float32)
test_y = np.square (test_x) - 0.5 + noise

# define placeholder for inputs to network
xs = tf.placeholder (tf.float32, [None, 1])
ys = tf.placeholder (tf.float32, [None, 1])

# ===================================================
# 网络
# 放到nn_load.nn_xx中

# add hidden layer
l1 = util.add_layer (weight_assign_op_list, xs, 1, 2, activation_function=tf.nn.relu)
# add output layer
prediction = util.add_layer (weight_assign_op_list, l1, 2, 1, activation_function=None)

accuracy = 1 - tf.reduce_mean (tf.reduce_sum (tf.square (ys - prediction), reduction_indices=[1]))

# ===================================================


# test_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/mnist/test_data/"
# test_x = np.load(test_data_dir + "test_images.npy")
# test_y = np.load(test_data_dir + "test_labels.npy")
#
# xs = tf.placeholder(tf.float32, [None, 784]) # 28x28
# ys = tf.placeholder(tf.float32, [None, 10])

# def add_layer (inputs, in_size, out_size, activation_function=None, ):
# 	Weights = tf.Variable (tf.random_normal ([in_size, out_size]))
# 	weight_holder = tf.placeholder (tf.float32, [in_size, out_size])
# 	weight_assign_op_list.append (tf.assign (Weights, weight_holder))
# 	biases = tf.Variable (tf.zeros ([1, out_size]) + 0.1, )
# 	biase_holder = tf.placeholder (tf.float32, [1, out_size])
# 	weight_assign_op_list.append (tf.assign (biases, biase_holder))
# 	Wx_plus_b = tf.matmul (inputs, Weights) + biases
# 	if activation_function is None:
# 		outputs = Wx_plus_b
# 	else:
# 		outputs = activation_function (Wx_plus_b, )
# 	return outputs


# first_layer = add_layer (xs, 784, 200, activation_function=tf.nn.sigmoid)
# second_layer = add_layer (first_layer, 200, 200, activation_function=tf.nn.sigmoid)
# prediction = add_layer (second_layer, 200, 10, activation_function=tf.nn.softmax)

# correct_prediction = tf.equal (tf.argmax (prediction, 1), tf.argmax (ys, 1))
# accuracy = tf.reduce_mean (tf.cast (correct_prediction, tf.float32))

weights = tf.trainable_variables ()

sess = tf.Session (config=config)
sess.run (tf.global_variables_initializer ())

app = Flask (__name__)
executor = ThreadPoolExecutor (1)

# 已回传参数的客户端数量
received_client_count = 0
# 存放各客户端回传参数的列表
received_client_weight = []
communication_round_count = 0


def calculate_avg_weight ():
	# 整合参数
	# router.G.py calculate_weight
	# 先存下第0个client的参数|W|，顺便初始化格式
	total_weight = received_client_weight [0]
	for weight_index in range (1, len (received_client_weight)):
		tmp_weight = []
		# 依次取出从1开始的client的参数|W|
		this_weight = received_client_weight [weight_index]
		# |w0, w1...|逐位累加
		for i in range (len (total_weight)):
			tmp_weight.append (np.sum ([total_weight [i], this_weight [i]], axis=0))
		total_weight = tmp_weight
	# total_weight = |w0_sum, w1_sum...|

	global received_client_count
	# 计算每位的平均参数
	avg_weight = [each_total_weight / received_client_count for each_total_weight in total_weight]
	# avg_weight = |w0_avg, w1_avg...|

	# 把接收到的权重赋值给当前网络
	weight_placeholder_start_index = 2
	# weight_assign_op_list = [tf.assign (weights, weight_holder), tf.assign (biases, biases_holder)...]
	# 指向网络中所有权重的指针，通过weight_assign_op_list可以直接向网络的权重赋值
	for w, r in zip (weight_assign_op_list, avg_weight):
		sess.run (w, feed_dict={"Placeholder_" + str (weight_placeholder_start_index) + ":0": r})
		weight_placeholder_start_index += 1
	global communication_round_count
	communication_round_count += 1

	# 测试一下效果，写日志，清缓存
	logging.info ('communication round {}:accuracy={}'.format (communication_round_count,
	                                                           sess.run (accuracy, feed_dict={xs: test_x, ys: test_y})))
	received_client_count = 0
	received_client_weight.clear ()

	# 向下一轮节点发送整合后的参数
	# 这个在util中做成一个接口save file的接口
	central_weights = io.BytesIO ()
	np.save (central_weights, avg_weight, allow_pickle=True)
	central_weights.seek (0)
	file = {'central_weights': central_weights}

	# 这个在util中做成generate client一个接口
	selected_client_list = np.random.choice (client_num, int (client_num * fraction_each_round), replace=False)

	# 向选好的节点发送数据
	for selected_client_index in selected_client_list:
		logging.info ("client_{} selected".format (selected_client_index))
		requests.post (
			"http://localhost:" + str (all_addresses [selected_client_index]) + "/update_weights_then_training",
			files=file)
		central_weights.seek (0)
		file = {'central_weights': central_weights}


@app.route ('/combine_weight', methods=['POST'])
def receive_weight ():
	# 接收参数并存起来
	# router.G.py receive_weight
	global communication_round_count
	if communication_round_count == communication_round_time:
		print (
			"=============================================================training ended====================================================================")
		return "training ended"
	global received_client_count
	global lock
	lock.acquire ()
	# 追加client的参数到received_client_weight
	received_client_weight.append (np.load (request.files.get ('client_weights'), allow_pickle=True))
	# logging.info("received weights: {}".format(received_client_weight[0]))
	received_client_count = received_client_count + 1
	lock.release ()
	# 判断一下接收够了没有
	global client_num
	if received_client_count == int (client_num * fraction_each_round):
		executor.submit (calculate_avg_weight)
	return "server gets local weight"


# 运行
@app.route ('/start', methods=['GET'])
def start ():
	logging.info ('communication round 0: accuracy={}'.format (sess.run (accuracy, feed_dict={xs: test_x, ys: test_y})))
	initial_weights = sess.run (weights)
	central_weights = io.BytesIO ()
	np.save (central_weights, initial_weights, allow_pickle=True)
	central_weights.seek (0)
	file = {'central_weights': central_weights}

	# move to util
	selected_client_list = np.random.choice (client_num, int (client_num * fraction_each_round), replace=False)

	for selected_client_index in selected_client_list:
		logging.debug ("client {} selected".format (selected_client_index))
		requests.post (
			"http://localhost:" + str (all_addresses [selected_client_index]) + "/update_weights_then_training",
			files=file)
		central_weights.seek (0)
		file = {'central_weights': central_weights}
	global communication_round_count
	communication_round_count += 1
	return 'start\n'


app.run (port=8888, threaded=True)
