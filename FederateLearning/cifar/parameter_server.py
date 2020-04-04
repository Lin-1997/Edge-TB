
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

config = tf.ConfigProto()
config.gpu_options.allow_growth = True

client_num = 2
fraction_each_round = 0.5
start_port = 9990
communication_round_time = 40
all_addresses = []

logging.basicConfig(level=logging.INFO,
                    filename='log/parameter_server.log',
                    filemode='w',
                    format=
                    '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                    )

lock = threading.Lock()

try:
	options, args = getopt.getopt(sys.argv[1:], "n:c:r:", ["client_num=", "fraction=", "communication_round_time="])
except getopt.GetoptError:
	sys.exit()

for option, value in options:
	if option in ("-n", "--client_num"):
		client_num = int(value)
	if option in ("-c", "--fraction"):
		fraction_each_round = float(value)
	if option in ("-r", "--communication_round_time"):
		communication_round_time = int(value)
if len(args) > 0:
	print("error args: {0}".format(args))

for client_index in range(client_num):
	all_addresses.append(start_port + client_index)

test_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/cifar10/test_data/"
test_x = np.load(test_data_dir + "test_images.npy")
test_y = np.load(test_data_dir + "test_labels.npy")

one_hot_encoder = np.eye(10)
one_hot_test_labels = one_hot_encoder[test_y][:, 0]

xs = tf.placeholder(tf.float32, [None, 32, 32, 3]) # 28x28
ys = tf.placeholder(tf.float32, [None, 10])
weight_assign_op_list = []

w_conv1 = tf.Variable(tf.truncated_normal([3, 3, 3, 32], stddev=0.1))
weight_assign_op_list.append(tf.assign(w_conv1, tf.placeholder(tf.float32, [3, 3, 3, 32])))
b_conv1 = tf.Variable(tf.zeros([1, 32]) + 0.1,)
weight_assign_op_list.append(tf.assign(b_conv1, tf.placeholder(tf.float32, [1, 32])))
h_conv1 = tf.nn.relu(tf.nn.conv2d(xs, w_conv1, strides=[1, 1, 1, 1], padding='VALID') + b_conv1)
h_pool1 = tf.nn.max_pool(h_conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

w_conv2 = tf.Variable(tf.truncated_normal([3, 3, 32, 64], stddev=-0.1))
weight_assign_op_list.append(tf.assign(w_conv2, tf.placeholder(tf.float32, [3, 3, 32, 64])))
b_conv2 = tf.Variable(tf.zeros([1, 64]) + 0.1,)
weight_assign_op_list.append(tf.assign(b_conv2, tf.placeholder(tf.float32, [1, 64])))
h_conv2 = tf.nn.relu(tf.nn.conv2d(h_pool1, w_conv2, strides=[1, 1, 1, 1], padding='VALID') + b_conv2)
h_pool2 = tf.nn.max_pool(h_conv2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

w_conv3 = tf.Variable(tf.truncated_normal([3, 3, 64, 64], stddev=0.1))
weight_assign_op_list.append(tf.assign(w_conv3, tf.placeholder(tf.float32, [3, 3, 64, 64])))
b_conv3 = tf.Variable(tf.zeros([1, 64]) + 0.1,)
weight_assign_op_list.append(tf.assign(b_conv3, tf.placeholder(tf.float32, [1, 64])))
h_conv3 = tf.nn.relu(tf.nn.conv2d(h_pool2, w_conv3, strides=[1, 1, 1, 1], padding='VALID') + b_conv3)

full_connected_layer1 = tf.Variable(tf.truncated_normal([1024, 64], stddev=0.1))
weight_assign_op_list.append(tf.assign(full_connected_layer1, tf.placeholder(tf.float32, [1024, 64])))
biases1 = tf.Variable(tf.zeros([1, 64]) + 0.1,)
weight_assign_op_list.append(tf.assign(biases1, tf.placeholder(tf.float32, [1, 64])))
output1 = tf.nn.relu(tf.matmul(tf.reshape(h_conv3, [-1, 4 * 4 * 64]), full_connected_layer1) + biases1)

full_connected_layer2 = tf.Variable(tf.truncated_normal([64, 10], stddev=0.1))
weight_assign_op_list.append(tf.assign(full_connected_layer2, tf.placeholder(tf.float32, [64, 10])))
biases2 = tf.Variable(tf.zeros([1, 10]) + 0.1,)
weight_assign_op_list.append(tf.assign(biases2, tf.placeholder(tf.float32, [1, 10])))
prediction = tf.nn.softmax(tf.matmul(output1, full_connected_layer2) + biases2)

correct_prediction = tf.equal(tf.argmax(prediction, 1), tf.argmax(ys, 1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

weights = tf.trainable_variables()

sess = tf.Session(config=config)
sess.run(tf.global_variables_initializer())

app = Flask(__name__)
executor = ThreadPoolExecutor(1)

# 已回传参数的客户端数量
received_client_count = 0;
# 存放各客户端回传参数的列表
received_client_weight = []
communication_round_count = 0

def calculate_avg_weight():
	total_weight = received_client_weight[0]
	for weight_index in range(1, len(received_client_weight)):
		tmp_weight = []
		this_weight = received_client_weight[weight_index]
		for i in range(len(total_weight)):
			tmp_weight.append(np.sum([total_weight[i], this_weight[i]], axis=0))
		total_weight = tmp_weight
	global received_client_count
	avg_weight = [each_total_weight / received_client_count for each_total_weight in total_weight]
	weight_placeholder_start_index = 2;
	for w, r in zip(weight_assign_op_list, avg_weight):
		sess.run(w, feed_dict={"Placeholder_" + str(weight_placeholder_start_index) + ":0": r})
		weight_placeholder_start_index += 1
	global communication_round_count
	communication_round_count += 1
	logging.info('communication round {}:accuracy={}'.format(communication_round_count, sess.run(accuracy, feed_dict={xs: test_x, ys: one_hot_test_labels})))
	received_client_count = 0
	received_client_weight.clear()
	central_weights = io.BytesIO()
	np.save(central_weights, avg_weight, allow_pickle=True)
	central_weights.seek(0)
	file = {'central_weights': central_weights}
	selected_client_list = np.random.choice(client_num, int(client_num * fraction_each_round), replace=False)
	for selected_client_index in selected_client_list:
		logging.info("client_{} selected".format(selected_client_index))
		requests.post("http://localhost:" + str(all_addresses[selected_client_index]) + "/update_weights_then_training",
		              files=file)
		central_weights.seek(0)
		file = {'central_weights': central_weights}

@app.route('/combine_weight', methods=['POST'])
def receive_weight():
	global communication_round_count
	if communication_round_count == communication_round_time:
		print("=============================================================training ended====================================================================")
		return "training ended"
	global received_client_count
	global lock
	lock.acquire()
	received_client_weight.append(np.load(request.files.get('client_weights'), allow_pickle=True))
	# logging.info("received weights: {}".format(received_client_weight[0]))
	received_client_count = received_client_count + 1
	lock.release()
	global client_num
	if received_client_count == int(client_num * fraction_each_round):
		executor.submit(calculate_avg_weight)
	return "server gets local weight"

@app.route('/start', methods=['GET'])
def start():
	logging.info('communication round 0: accuracy={}'.format(sess.run(accuracy, feed_dict={xs: test_x, ys: one_hot_test_labels})))
	initial_weights = sess.run(weights)
	central_weights = io.BytesIO()
	np.save(central_weights, initial_weights, allow_pickle=True)
	central_weights.seek(0)
	file = {'central_weights': central_weights}
	selected_client_list = np.random.choice(client_num, int(client_num * fraction_each_round), replace=False)
	for selected_client_index in selected_client_list:
		logging.debug("client {} selected".format(selected_client_index))
		requests.post("http://localhost:" + str(all_addresses[selected_client_index]) + "/update_weights_then_training", files=file)
		central_weights.seek(0)
		file = {'central_weights': central_weights}
	global communication_round_count
	communication_round_count += 1
	return 'start'

app.run(port=8888, threaded=True)