import tensorflow as tf
from tensorflow.keras import datasets
import numpy as np

config = tf.ConfigProto()
config.gpu_options.allow_growth = True

epoch_num = 40
batch_size = 32
learning_rate = 0.05
client_num = 20
iid_data_num = 100

each_client_iid_data_num = int(iid_data_num / client_num)

train_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/cifar10/iid/"
test_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/cifar10/test_data/"
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

# Normalize pixel values to be between 0 and 1
one_hot_encoder = np.eye(10)
one_hot_train_labels = one_hot_encoder[data_y.astype("int")][:, 0]
one_hot_test_labels = one_hot_encoder[test_y][:, 0]

train_data = tf.data.Dataset.from_tensor_slices((data_x, one_hot_train_labels))
train_data = train_data.shuffle(buffer_size=1000)
train_data = train_data.batch(batch_size).repeat(epoch_num)
iters = train_data.make_one_shot_iterator()
batch = iters.get_next()

xs = tf.placeholder(tf.float32, [None, 32, 32, 3])
ys = tf.placeholder(tf.float32, [None, 10])

w_conv1 = tf.Variable(tf.truncated_normal([3, 3, 3, 32], stddev=0.1))
b_conv1 = tf.Variable(tf.zeros([1, 32]) + 0.1,)
h_conv1 = tf.nn.relu(tf.nn.conv2d(xs, w_conv1, strides=[1, 1, 1, 1], padding='VALID') + b_conv1)
h_pool1 = tf.nn.max_pool(h_conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

w_conv2 = tf.Variable(tf.truncated_normal([3, 3, 32, 64], stddev=-0.1))
b_conv2 = tf.Variable(tf.zeros([1, 64]) + 0.1,)
h_conv2 = tf.nn.relu(tf.nn.conv2d(h_pool1, w_conv2, strides=[1, 1, 1, 1], padding='VALID') + b_conv2)
h_pool2 = tf.nn.max_pool(h_conv2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

w_conv3 = tf.Variable(tf.truncated_normal([3, 3, 64, 64], stddev=0.1))
b_conv3 = tf.Variable(tf.zeros([1, 64]) + 0.1,)
h_conv3 = tf.nn.relu(tf.nn.conv2d(h_pool2, w_conv3, strides=[1, 1, 1, 1], padding='VALID') + b_conv3)

full_connected_layer1 = tf.Variable(tf.truncated_normal([1024, 64], stddev=0.1))
biases1 = tf.Variable(tf.zeros([1, 64]) + 0.1,)
output1 = tf.nn.relu(tf.matmul(tf.reshape(h_conv3, [-1, 4 * 4 * 64]), full_connected_layer1) + biases1)

full_connected_layer2 = tf.Variable(tf.truncated_normal([64, 10], stddev=0.1))
biases2 = tf.Variable(tf.zeros([1, 10]) + 0.1,)
prediction = tf.nn.softmax(tf.matmul(output1, full_connected_layer2) + biases2)

# the error between prediction and real data
cross_entropy = tf.reduce_mean(-tf.reduce_sum(ys * tf.log(prediction + 1e-10),
                                              reduction_indices=[1]))       # loss

global_step = tf.Variable(tf.constant(0))
lr = tf.train.exponential_decay(learning_rate, global_step=global_step, decay_steps=1, decay_rate=0.9, staircase=True)

train_step = tf.train.GradientDescentOptimizer(lr).minimize(cross_entropy)
# train_step = tf.train.AdamOptimizer(1e-4).minimize(cross_entropy)
correct_prediction = tf.equal(tf.argmax(prediction, 1), tf.argmax(ys, 1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

sess = tf.Session(config=config)
sess.run(tf.global_variables_initializer())

for epoch in range(int(epoch_num)):
    for iter in range(int(len(data_x) / batch_size)):
        batch_data = sess.run(batch)
        loss_val, _ = sess.run([cross_entropy, train_step], feed_dict={xs:batch_data[0], ys:batch_data[1], global_step:epoch})
    print('epoch {}:loss={}'.format(epoch, loss_val))
    # print('epoch {}:accuracy={}'.format(epoch, sess.run(accuracy, feed_dict={xs: test_x, ys: one_hot_test_labels})))