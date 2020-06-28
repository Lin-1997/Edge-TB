import numpy as np
import tensorflow as tf

nn = {}

assign_list = []

test_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/cifar10/test_data/"
# 下面还有个train_data_dir也要改
test_x = np.load (test_data_dir + "test_images.npy")
test_y = np.load (test_data_dir + "test_labels.npy")
one_hot_encoder = np.eye (10)
one_hot_test_labels = one_hot_encoder [test_y] [:, 0]

xs = tf.placeholder (tf.float32, [None, 32, 32, 3])
ys = tf.placeholder (tf.float32, [None, 10])

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
config = tf.ConfigProto ()
# config.gpu_options.allow_growth = True
sess = tf.Session (config=config)
sess.run (tf.global_variables_initializer ())

nn ['test_x'] = test_x
# one_hot_test_labels acts as test_y
nn ['test_y'] = one_hot_test_labels
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
	train_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/cifar10/iid/"
	train_x_list = []
	train_y_list = []
	for train_data_index in range (end_index - start_index):
		train_x_list.append (np.load (train_data_dir + "train_images_" + str (start_index + train_data_index) + ".npy"))
		train_y_list.append (np.load (train_data_dir + "train_labels_" + str (start_index + train_data_index) + ".npy"))
	train_x = np.concatenate (tuple (train_x_list))
	train_y = np.concatenate (tuple (train_y_list))

	# one_hot_train_labels acts as train_y
	one_hot_train_labels = one_hot_encoder [train_y.astype ("int")] [:, 0]

	train_data = tf.data.Dataset.from_tensor_slices ((train_x, one_hot_train_labels))
	train_data = train_data.shuffle (buffer_size=10000)
	train_data = train_data.batch (bs).repeat (r)
	i = train_data.make_one_shot_iterator ()
	nn ['batch'] = i.get_next ()
	nn ['batch_num'] = int (len (train_x) / bs)


def set_train_lr (lr):
	train_step = tf.train.GradientDescentOptimizer (lr).minimize (loss)
	nn ['train_step'] = train_step
