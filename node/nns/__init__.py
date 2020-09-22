from abc import abstractmethod

import tensorflow as tf


class NN (object):
	@staticmethod
	def conv (assign_list, inputs, kernel_size, channel_in, channel_out, stride_size, activation_function,
			stddev=1.0, keep=1.0, padding='SAME'):
		w = tf.Variable (tf.truncated_normal ([kernel_size, kernel_size, channel_in, channel_out], stddev=stddev))
		assign_list.append (
			tf.assign (w, tf.placeholder (tf.float32, [kernel_size, kernel_size, channel_in, channel_out])))
		b = tf.Variable (tf.zeros ([1, channel_out]) + 0.1)
		assign_list.append (tf.assign (b, tf.placeholder (tf.float32, [1, channel_out])))
		return tf.nn.dropout (activation_function (
			tf.nn.conv2d (inputs, w, strides=[1, stride_size, stride_size, 1], padding=padding) + b), keep)

	@staticmethod
	def pool (inputs, kernel_size, stride_size, pooling, padding='SAME'):
		return pooling (inputs, ksize=[1, kernel_size, kernel_size, 1], strides=[1, stride_size, stride_size, 1],
			padding=padding)

	@staticmethod
	def fc (assign_list, inputs, in_size, out_size, activation_function, stddev=1.0):
		w = tf.Variable (tf.random_normal ([in_size, out_size], stddev=stddev))
		assign_list.append (tf.assign (w, tf.placeholder (tf.float32, [in_size, out_size])))
		b = tf.Variable (tf.zeros ([1, out_size]) + 0.1)
		assign_list.append (tf.assign (b, tf.placeholder (tf.float32, [1, out_size])))
		return activation_function (tf.matmul (inputs, w) + b)

	def __init__ (self, _test_x, _test_y, _xs, _ys, _assign_list, _loss, _accuracy, _weights, _sess, _size, _path):
		self.test_x = _test_x
		self.test_y = _test_y
		self.xs = _xs
		self.ys = _ys
		self.assign_list = _assign_list
		self.loss = _loss
		self.accuracy = _accuracy
		self.weights = _weights
		self.sess = _sess
		self.size = _size
		self.path = _path
		self.batch_size = None
		self.batch_num = None
		self.batch = None
		self.train_step = None

	@abstractmethod
	def set_batch (self, batch_size, round_repeat, start_index, end_index):
		# Assign value to self.batch_size, self.batch_num and self.batch
		# Refer to nn_mnist.py and nn_cifar10.py
		pass

	@abstractmethod
	def set_train_step (self, lr):
		# Assign value to self.train_step
		# Refer to nn_mnist.py and nn_cifar10.py
		pass
