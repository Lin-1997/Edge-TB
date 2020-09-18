import os

import numpy as np
import tensorflow as tf

import nns
import util


class Mnist (nns.NN):
	def __init__ (self, _test_x, _test_y, _xs, _ys, _assign_list, _loss, _accuracy, _weights, _sess, _size, _path):
		super ().__init__ (_test_x, _test_y, _xs, _ys, _assign_list, _loss, _accuracy, _weights, _sess, _size, _path)

	def set_train_data_batch (self, batch_size, round_repeat, start_index, end_index):
		train_data_dir = self.path + '/train_data'
		train_x_list = []
		train_y_list = []
		for i in range (end_index - start_index + 1):
			train_x_list.append (
				np.load (train_data_dir + '/images_' + str (start_index + i) + '.npy').reshape ([-1, 784]))
			train_y_list.append (
				np.load (train_data_dir + '/labels_' + str (start_index + i) + '.npy').reshape ([-1, 10]))
		train_x = np.concatenate (tuple (train_x_list))
		train_y = np.concatenate (tuple (train_y_list))

		train_data = tf.data.Dataset.from_tensor_slices ((train_x, train_y))
		train_data = train_data.shuffle (buffer_size=10000)
		train_data = train_data.batch (batch_size).repeat (round_repeat)
		i = train_data.make_one_shot_iterator ()
		self.batch = i.get_next ()
		self.batch_num = int (len (train_x) / batch_size)


MINST_path = os.path.abspath (os.path.join (os.path.dirname (__file__), '../datasets/MNIST'))
test_x = np.load (MINST_path + '/test_data/images.npy').reshape ([-1, 784])
test_y = np.load (MINST_path + '/test_data/labels.npy').reshape ([-1, 10])

xs = tf.placeholder (tf.float32, [None, 784])
ys = tf.placeholder (tf.float32, [None, 10])

assign_list = []
l1 = nns.NN.add_layer (assign_list, xs, 784, 200, activation_function=tf.nn.sigmoid)
l2 = nns.NN.add_layer (assign_list, l1, 200, 200, activation_function=tf.nn.sigmoid)
prediction = nns.NN.add_layer (assign_list, l2, 200, 10, activation_function=tf.nn.softmax)

loss = tf.reduce_mean (-tf.reduce_sum (ys * tf.log (prediction + 1e-10), reduction_indices=[1]))
correct_prediction = tf.equal (tf.argmax (prediction, 1), tf.argmax (ys, 1))
accuracy = tf.reduce_mean (tf.cast (correct_prediction, tf.float32))

weights = tf.trainable_variables ()
sess = tf.Session ()
sess.run (tf.global_variables_initializer ())
size = util.calculate_size (sess.run (weights))

nn = Mnist (test_x, test_y, xs, ys, assign_list, loss, accuracy, weights, sess, size, MINST_path)
