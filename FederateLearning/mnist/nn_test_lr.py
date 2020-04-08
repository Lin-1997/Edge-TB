import numpy as np
import tensorflow as tf
import util

nn_test = {}
assign_list = []

test_x = np.array (
	[-0.99, -0.89, -0.79, -0.69, -0.59, -0.49, -0.39, -0.29, -0.19, -0.09, 0.09, 0.19, 0.29, 0.39, 0.49, 0.59,
	 0.69, 0.79, 0.89, 0.99]) [:, np.newaxis]
noise = np.random.normal (0, 0.05, test_x.shape).astype (np.float32)
test_y = np.square (test_x) - 0.5 + noise

# define placeholder for inputs to network
xs = tf.placeholder (tf.float32, [None, 1])
ys = tf.placeholder (tf.float32, [None, 1])

l1 = util.add_layer (assign_list, xs, 1, 2, activation_function=tf.nn.relu)
prediction = util.add_layer (assign_list, l1, 2, 1, activation_function=None)

accuracy = 1 - tf.reduce_mean (tf.reduce_sum (tf.square (ys - prediction), reduction_indices=[1]))

weights = tf.trainable_variables ()

config = tf.ConfigProto ()
# config.gpu_options.allow_growth = True
sess = tf.Session (config=config)
sess.run (tf.global_variables_initializer ())

nn_test ['test_x'] = test_x
nn_test ['test_y'] = test_y
nn_test ['xs'] = xs
nn_test ['ys'] = ys
nn_test ['assign_list'] = assign_list
nn_test ['accuracy'] = accuracy
nn_test ['weights'] = weights
nn_test ['sess'] = sess


def get_nn ():
	return nn_test
