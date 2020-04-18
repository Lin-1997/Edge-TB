import numpy as np
import tensorflow as tf

import util

nn = {}

assign_list = []

test_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/mnist/test_data/"
test_x = np.load (test_data_dir + "test_images.npy")
test_y = np.load (test_data_dir + "test_labels.npy")

xs = tf.placeholder (tf.float32, [None, 784])
ys = tf.placeholder (tf.float32, [None, 10])

l1 = util.add_layer (assign_list, xs, 784, 200, activation_function=tf.nn.sigmoid)
l2 = util.add_layer (assign_list, l1, 200, 200, activation_function=tf.nn.sigmoid)
prediction = util.add_layer (assign_list, l2, 200, 10, activation_function=tf.nn.softmax)

loss = tf.reduce_mean (-tf.reduce_sum (ys * tf.log (prediction + 1e-10), reduction_indices=[1]))
correct_prediction = tf.equal (tf.argmax (prediction, 1), tf.argmax (ys, 1))
accuracy = tf.reduce_mean (tf.cast (correct_prediction, tf.float32))

weights = tf.trainable_variables ()
config = tf.ConfigProto ()
# config.gpu_options.allow_growth = True
sess = tf.Session (config=config)
sess.run (tf.global_variables_initializer ())

nn ['test_x'] = test_x
nn ['test_y'] = test_y
nn ['xs'] = xs
nn ['ys'] = ys
nn ['assign_list'] = assign_list
nn ['loss'] = loss
nn ['accuracy'] = accuracy
nn ['weights'] = weights
nn ['sess'] = sess


def get_nn ():
	return nn


def set_train_data_batch (bs, r, start_index, end_index):
	train_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/mnist/iid/"
	train_x_list = []
	train_y_list = []
	for train_data_index in range (end_index - start_index):
		train_x_list.append (np.load (train_data_dir + "train_images_" + str (start_index + train_data_index) + ".npy"))
		train_y_list.append (np.load (train_data_dir + "train_labels_" + str (start_index + train_data_index) + ".npy"))
	train_x = np.concatenate (tuple (train_x_list))
	train_y = np.concatenate (tuple (train_y_list))

	train_data = tf.data.Dataset.from_tensor_slices ((train_x, train_y))
	train_data = train_data.shuffle (buffer_size=10000)
	train_data = train_data.batch (bs).repeat (r)
	i = train_data.make_one_shot_iterator ()
	nn ['batch'] = i.get_next ()
	nn ['batch_num'] = int (len (train_x) / bs)


def set_train_lr (lr):
	train_step = tf.train.GradientDescentOptimizer (lr).minimize (loss)
	nn ['train_step'] = train_step
