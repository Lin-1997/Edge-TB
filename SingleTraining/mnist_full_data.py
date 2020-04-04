from __future__ import print_function
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
import numpy as np

config = tf.ConfigProto()
config.gpu_options.allow_growth = True

epoch_num = 40
batch_size = 32
learning_rate = 0.5

mnist_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/mnist/whole_data/"
# number 1 to 10 data
mnist = input_data.read_data_sets(mnist_data_dir, one_hot=True)
train_images = mnist.train.images
train_labels = mnist.train.labels
validate_images = mnist.validation.images
validate_labels = mnist.validation.labels

total_train_images = np.concatenate((train_images, validate_images))
total_train_labels = np.concatenate((train_labels, validate_labels))
hstacked_train_data = np.hstack((total_train_images, total_train_labels))
np.random.shuffle(hstacked_train_data)
train_images = hstacked_train_data[:, :784]
train_labels = hstacked_train_data[:, 784:]

train_data = tf.data.Dataset.from_tensor_slices((train_images, train_labels))
train_data = train_data.shuffle(buffer_size=1000)
train_data = train_data.batch(batch_size).repeat(epoch_num)
iters = train_data.make_one_shot_iterator()
batch = iters.get_next()

xs = tf.placeholder(tf.float32, [None, 784])
ys = tf.placeholder(tf.float32, [None, 10])

def add_layer(inputs, in_size, out_size, activation_function=None,):
	Weights = tf.Variable(tf.random_normal([in_size, out_size]))
	biases = tf.Variable(tf.zeros([1, out_size]) + 0.1,)
	Wx_plus_b = tf.matmul(inputs, Weights) + biases
	if activation_function is None:
		outputs = Wx_plus_b
	else:
		outputs = activation_function(Wx_plus_b,)
	return outputs

first_layer = add_layer(xs, 784, 200, activation_function=tf.nn.sigmoid)
second_layer = add_layer(first_layer, 200, 200, activation_function=tf.nn.sigmoid)
prediction = add_layer(second_layer, 200, 10,  activation_function=tf.nn.softmax)

# the error between prediction and real data
cross_entropy = tf.reduce_mean(-tf.reduce_sum(ys * tf.log(prediction + 1e-10),
                                              reduction_indices=[1]))       # loss
train_step = tf.train.GradientDescentOptimizer(learning_rate).minimize(cross_entropy)

correct_prediction = tf.equal(tf.argmax(prediction, 1), tf.argmax(ys, 1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

sess = tf.Session(config=config)
sess.run(tf.global_variables_initializer())

for epoch in range(int(epoch_num)):
	for iter in range(int(len(train_images) / batch_size)):
		batch_data = sess.run(batch)
		loss_val, _ = sess.run([cross_entropy, train_step], feed_dict={xs:batch_data[0], ys:batch_data[1]})
	print('epoch {}:loss={}'.format(epoch, loss_val))
	print('epoch {}:accuracy={}'.format(epoch, sess.run(accuracy, feed_dict={xs: mnist.test.images, ys: mnist.test.labels})))
