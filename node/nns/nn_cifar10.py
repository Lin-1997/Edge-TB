import os

import numpy as np
import tensorflow as tf

import nns
import util


class Cifar10 (nns.NN):
	def __init__ (self, _test_x, _test_y, _xs, _ys, _assign_list, _loss, _accuracy, _weights, _sess, _size, _path):
		super ().__init__ (_test_x, _test_y, _xs, _ys, _assign_list, _loss, _accuracy, _weights, _sess, _size, _path)

	def set_batch (self, batch_size, round_repeat, start_index, end_index):
		train_data_dir = self.path + '/train_data'
		train_x_list = []
		train_y_list = []
		for i in range (end_index - start_index + 1):
			train_x_list.append (
				np.load (train_data_dir + '/images_' + str (start_index + i) + '.npy').reshape ([-1, 32, 32, 3]))
			train_y_list.append (np.load (train_data_dir + '/labels_' + str (start_index + i) + '.npy'))
		train_x = np.concatenate (tuple (train_x_list))
		train_y = np.concatenate (tuple (train_y_list))

		train_data = tf.data.Dataset.from_tensor_slices ((train_x, train_y))
		train_data = train_data.shuffle (buffer_size=10000)
		train_data = train_data.batch (batch_size).repeat (round_repeat)
		i = train_data.make_one_shot_iterator ()
		self.batch_size = batch_size
		self.batch_num = int (len (train_x) / batch_size)
		self.batch = i.get_next ()

	def set_train_step (self, lr):
		self.train_step = tf.train.GradientDescentOptimizer (lr).minimize (self.loss)


path = os.path.abspath (os.path.join (os.path.dirname (__file__), '../datasets/CIFAR10'))
test_x = np.load (path + '/test_data/images.npy').reshape ([-1, 32, 32, 3])
test_y = np.load (path + '/test_data/labels.npy')

xs = tf.placeholder (tf.float32, [None, 32, 32, 3])
ys = tf.placeholder (tf.float32, [None, 10])

assign_list = []
w_conv1 = tf.Variable (tf.truncated_normal ([3, 3, 3, 32], stddev=0.1))
assign_list.append (tf.assign (w_conv1, tf.placeholder (tf.float32, [3, 3, 3, 32])))
b_conv1 = tf.Variable (tf.zeros ([1, 32]) + 0.1, )
assign_list.append (tf.assign (b_conv1, tf.placeholder (tf.float32, [1, 32])))
h_conv1 = tf.nn.relu (tf.nn.conv2d (xs, w_conv1, strides=[1, 1, 1, 1], padding='VALID') + b_conv1)
h_pool1 = tf.nn.max_pool (h_conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

w_conv2 = tf.Variable (tf.truncated_normal ([3, 3, 32, 64], stddev=-0.1))
assign_list.append (tf.assign (w_conv2, tf.placeholder (tf.float32, [3, 3, 32, 64])))
b_conv2 = tf.Variable (tf.zeros ([1, 64]) + 0.1, )
assign_list.append (tf.assign (b_conv2, tf.placeholder (tf.float32, [1, 64])))
h_conv2 = tf.nn.relu (tf.nn.conv2d (h_pool1, w_conv2, strides=[1, 1, 1, 1], padding='VALID') + b_conv2)
h_pool2 = tf.nn.max_pool (h_conv2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

w_conv3 = tf.Variable (tf.truncated_normal ([3, 3, 64, 64], stddev=0.1))
assign_list.append (tf.assign (w_conv3, tf.placeholder (tf.float32, [3, 3, 64, 64])))
b_conv3 = tf.Variable (tf.zeros ([1, 64]) + 0.1, )
assign_list.append (tf.assign (b_conv3, tf.placeholder (tf.float32, [1, 64])))
h_conv3 = tf.nn.relu (tf.nn.conv2d (h_pool2, w_conv3, strides=[1, 1, 1, 1], padding='VALID') + b_conv3)

full_connected_layer1 = tf.Variable (tf.truncated_normal ([1024, 64], stddev=0.1))
assign_list.append (tf.assign (full_connected_layer1, tf.placeholder (tf.float32, [1024, 64])))
biases1 = tf.Variable (tf.zeros ([1, 64]) + 0.1, )
assign_list.append (tf.assign (biases1, tf.placeholder (tf.float32, [1, 64])))
output1 = tf.nn.relu (tf.matmul (tf.reshape (h_conv3, [-1, 4 * 4 * 64]), full_connected_layer1) + biases1)

full_connected_layer2 = tf.Variable (tf.truncated_normal ([64, 10], stddev=0.1))
assign_list.append (tf.assign (full_connected_layer2, tf.placeholder (tf.float32, [64, 10])))
biases2 = tf.Variable (tf.zeros ([1, 10]) + 0.1, )
assign_list.append (tf.assign (biases2, tf.placeholder (tf.float32, [1, 10])))

prediction = tf.nn.softmax (tf.matmul (output1, full_connected_layer2) + biases2)

loss = tf.reduce_mean (-tf.reduce_sum (ys * tf.log (prediction + 1e-10), reduction_indices=[1]))
correct_prediction = tf.equal (tf.argmax (prediction, 1), tf.argmax (ys, 1))
accuracy = tf.reduce_mean (tf.cast (correct_prediction, tf.float32))

weights = tf.trainable_variables ()
sess = tf.Session ()
sess.run (tf.global_variables_initializer ())
size = util.calculate_size (sess.run (weights))

nn = Cifar10 (test_x, test_y, xs, ys, assign_list, loss, accuracy, weights, sess, size, path)
