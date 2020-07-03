import numpy as np
import tensorflow as tf

import util

nn = {}

assign_list = []

test_x = np.array (
	[-0.99, -0.89, -0.79, -0.69, -0.59, -0.49, -0.39, -0.29, -0.19, -0.09, 0.09, 0.19, 0.29, 0.39, 0.49, 0.59,
	 0.69, 0.79, 0.89, 0.99]) [:, np.newaxis]
noise = np.random.normal (0, 0.05, test_x.shape).astype (np.float32)
test_y = np.square (test_x) - 0.5 + noise

train_x = np.array (
	[-0.99, -0.89, -0.79, -0.69, -0.59, -0.49, -0.39, -0.29, -0.19, -0.09, 0.09, 0.19, 0.29, 0.39, 0.49, 0.59,
	 0.69, 0.79, 0.89, 0.99]) [:, np.newaxis]
noise = np.random.normal (0, 0.05, train_x.shape).astype (np.float32)
train_y = np.square (train_x) - 0.5 + noise

xs = tf.placeholder (tf.float32, [None, 1])
ys = tf.placeholder (tf.float32, [None, 1])

l1 = util.add_layer (assign_list, xs, 1, 2, activation_function=tf.nn.relu)
prediction = util.add_layer (assign_list, l1, 2, 1, activation_function=None)

loss = tf.reduce_mean (tf.reduce_sum (tf.square (ys - prediction), reduction_indices=[1]))
accuracy = 1 - loss

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
nn ['size'] = util.calculate_size (sess.run (weights))


def get_nn ():
	return nn


# start_index, end_index are useless in LR
def set_train_data_batch (bs, r, start_index, end_index):
	train_data = tf.data.Dataset.from_tensor_slices ((train_x, train_y))
	train_data = train_data.shuffle (buffer_size=10000)
	train_data = train_data.batch (bs).repeat (r)
	i = train_data.make_one_shot_iterator ()
	nn ['batch'] = i.get_next ()
	nn ['batch_num'] = int (len (train_x) / bs)


def set_train_lr (lr):
	train_step = tf.train.GradientDescentOptimizer (lr).minimize (loss)
	nn ['train_step'] = train_step
