from __future__ import print_function
import tensorflow as tf
import numpy as np

config = tf.ConfigProto()
config.gpu_options.allow_growth = True

epoch_num = 40
batch_size = 32
learning_rate = 0.5
client_num = 50
iid_data_num = 100

each_client_iid_data_num = int(iid_data_num / client_num)

train_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/mnist/iid/"
test_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/mnist/test_data/"
data_x_list = []
data_y_list = []
start_index = 0
end_index = each_client_iid_data_num
for train_data_index in range(end_index - start_index):
	data_x_list.append(np.load(train_data_dir + "train_images_" + str(start_index + train_data_index) + ".npy"))
	data_y_list.append(np.load(train_data_dir + "train_labels_" + str(start_index + train_data_index) + ".npy"))
data_x = np.concatenate(tuple(data_x_list))
data_y = np.concatenate(tuple(data_y_list))
test_x = np.load(test_data_dir + "test_images.npy")
test_y = np.load(test_data_dir + "test_labels.npy")

train_data = tf.data.Dataset.from_tensor_slices((data_x, data_y))
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
	for iter in range(int(len(data_x) / batch_size)):
		batch_data = sess.run(batch)
		loss_val, _ = sess.run([cross_entropy, train_step], feed_dict={xs:batch_data[0], ys:batch_data[1]})
	print('epoch {}:loss={}'.format(epoch, loss_val))
	print('epoch {}:accuracy={}'.format(epoch, sess.run(accuracy, feed_dict={xs: test_x, ys: test_y})))
