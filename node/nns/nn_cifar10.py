import os

import numpy as np
import tensorflow as tf

from nns import NN
import util


class Cifar10 (NN):
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
		self.train_step = tf.train.AdamOptimizer (lr).minimize (self.loss)
		self.sess.run (tf.global_variables_initializer ())


path = os.path.abspath (os.path.join (os.path.dirname (__file__), '../datasets/CIFAR10'))
test_x = np.load (path + '/test_data/images.npy').reshape ([-1, 32, 32, 3])
test_y = np.load (path + '/test_data/labels.npy')

xs = tf.placeholder (tf.float32, [None, 32, 32, 3])
ys = tf.placeholder (tf.float32, [None, 10])

assign_list = []

conv1 = NN.conv (assign_list, xs, 3, 3, 32, 1, tf.nn.relu, 0.03, 0.8)
pool1 = NN.pool (conv1, 2, 2, tf.nn.max_pool)
conv2 = NN.conv (assign_list, pool1, 3, 32, 64, 1, tf.nn.relu, -0.03, 0.8)
pool2 = NN.pool (conv2, 2, 2, tf.nn.max_pool)
conv3 = NN.conv (assign_list, pool2, 3, 64, 128, 1, tf.nn.relu, 0.03, 0.8)
conv4 = NN.conv (assign_list, conv3, 3, 128, 128, 1, tf.nn.relu, -0.03, 0.8)
pool3 = NN.pool (conv4, 2, 2, tf.nn.max_pool)
fc1 = NN.fc (assign_list, tf.reshape (pool3, [-1, 4 * 4 * 128]), 4 * 4 * 128, 512, tf.nn.relu, 0.03)
fc2 = NN.fc (assign_list, fc1, 512, 64, tf.nn.relu, -0.03)
prediction = NN.fc (assign_list, fc2, 64, 10, tf.nn.softmax, 0.03)

loss = tf.reduce_mean (-tf.reduce_sum (ys * tf.log (prediction + 1e-10), reduction_indices=[1]))
correct_prediction = tf.equal (tf.argmax (prediction, 1), tf.argmax (ys, 1))
accuracy = tf.reduce_mean (tf.cast (correct_prediction, tf.float32))

weights = tf.trainable_variables ()
sess = tf.Session ()
sess.run (tf.global_variables_initializer ())
size = util.calculate_size (sess.run (weights))

nn = Cifar10 (test_x, test_y, xs, ys, assign_list, loss, accuracy, weights, sess, size, path)
