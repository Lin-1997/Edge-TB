import tensorflow as tf
import numpy as np
import io
import requests
import random
import threading
import getopt
import sys
import logging
from flask import Flask, request
from concurrent.futures import ThreadPoolExecutor

config = tf.ConfigProto()
config.gpu_options.allow_growth = True

start_port = 9990
epoch_num = 40
batch_size = 32
this_index = 0
client_num = 3
local_epoch_num = 1
learning_rate = 0.5
all_addresses = []

try:
    options, args = getopt.getopt(sys.argv[1:], "n:i:e:b:l::j:k", ["client_num=", "this_index=", "epoch_num=", "batch_size=",
                                                               "local_epoch_num=",  "start_data_index=", "end_data_index="])
except getopt.GetoptError:
    sys.exit()

for option, value in options:
    if option in ("-n", "--client_num"):
        client_num = int(value)
    if option in ("-i", "--this_index"):
        this_index = int(value)
    if option in ("-e", "--epoch_name"):
        epoch_num = int(value)
    if option in ("-b", "--batch_size"):
        batch_size = int(value)
    if option in ("-l", "--local_epoch_num"):
        local_epoch_num = int(value)
    if option in ("-j", "--start_data_index"):
        start_index = int(value)
    if option in ("-k", "--end_data_index"):
        end_index = int(value)
if len(args) > 0:
    print("error args: {0}".format(args))

for client_index in range(client_num):
    all_addresses.append(start_port + client_index)

this_address = all_addresses[this_index]
all_addresses.remove(this_address)

logging.basicConfig(level=logging.INFO,
                    filename='log/client_' + str(this_index) + '.log',
                    filemode='w',
                    format=
                    '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                    )

lock = threading.Lock()

train_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/cifar10/iid/"
test_data_dir = "/home/se-lab/Desktop/Data/EdgeAI/cifar10/test_data/"
data_x_list = []
data_y_list = []
for train_data_index in range(end_index - start_index):
    data_x_list.append(np.load(train_data_dir + "train_images_" + str(start_index + train_data_index) + ".npy"))
    data_y_list.append(np.load(train_data_dir + "train_labels_" + str(start_index + train_data_index) + ".npy"))
data_x = np.concatenate(tuple(data_x_list))
data_y = np.concatenate(tuple(data_y_list))
test_x = np.load(test_data_dir + "test_images.npy")
test_y = np.load(test_data_dir + "test_labels.npy")

one_hot_encoder = np.eye(10)
one_hot_train_labels = one_hot_encoder[data_y.astype("int")][:, 0]
one_hot_test_labels = one_hot_encoder[test_y][:, 0]

train_data = tf.data.Dataset.from_tensor_slices((data_x, one_hot_train_labels))
train_data = train_data.shuffle(buffer_size=10000)
train_data = train_data.batch(batch_size).repeat(epoch_num)
iters = train_data.make_one_shot_iterator()
batch = iters.get_next()


xs = tf.placeholder(tf.float32, [None, 32, 32, 3]) # 28x28
ys = tf.placeholder(tf.float32, [None, 10])
weight_assign_op_list = []

w_conv1 = tf.Variable(tf.truncated_normal([3, 3, 3, 32], stddev=0.1))
weight_assign_op_list.append(tf.assign(w_conv1, tf.placeholder(tf.float32, [3, 3, 3, 32])))
b_conv1 = tf.Variable(tf.zeros([1, 32]) + 0.1,)
weight_assign_op_list.append(tf.assign(b_conv1, tf.placeholder(tf.float32, [1, 32])))
h_conv1 = tf.nn.relu(tf.nn.conv2d(xs, w_conv1, strides=[1, 1, 1, 1], padding='VALID') + b_conv1)
h_pool1 = tf.nn.max_pool(h_conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

w_conv2 = tf.Variable(tf.truncated_normal([3, 3, 32, 64], stddev=-0.1))
weight_assign_op_list.append(tf.assign(w_conv2, tf.placeholder(tf.float32, [3, 3, 32, 64])))
b_conv2 = tf.Variable(tf.zeros([1, 64]) + 0.1,)
weight_assign_op_list.append(tf.assign(b_conv2, tf.placeholder(tf.float32, [1, 64])))
h_conv2 = tf.nn.relu(tf.nn.conv2d(h_pool1, w_conv2, strides=[1, 1, 1, 1], padding='VALID') + b_conv2)
h_pool2 = tf.nn.max_pool(h_conv2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='VALID')

w_conv3 = tf.Variable(tf.truncated_normal([3, 3, 64, 64], stddev=0.1))
weight_assign_op_list.append(tf.assign(w_conv3, tf.placeholder(tf.float32, [3, 3, 64, 64])))
b_conv3 = tf.Variable(tf.zeros([1, 64]) + 0.1,)
weight_assign_op_list.append(tf.assign(b_conv3, tf.placeholder(tf.float32, [1, 64])))
h_conv3 = tf.nn.relu(tf.nn.conv2d(h_pool2, w_conv3, strides=[1, 1, 1, 1], padding='VALID') + b_conv3)

full_connected_layer1 = tf.Variable(tf.truncated_normal([1024, 64], stddev=0.1))
weight_assign_op_list.append(tf.assign(full_connected_layer1, tf.placeholder(tf.float32, [1024, 64])))
biases1 = tf.Variable(tf.zeros([1, 64]) + 0.1,)
weight_assign_op_list.append(tf.assign(biases1, tf.placeholder(tf.float32, [1, 64])))
output1 = tf.nn.relu(tf.matmul(tf.reshape(h_conv3, [-1, 4 * 4 * 64]), full_connected_layer1) + biases1)

full_connected_layer2 = tf.Variable(tf.truncated_normal([64, 10], stddev=0.1))
weight_assign_op_list.append(tf.assign(full_connected_layer2, tf.placeholder(tf.float32, [64, 10])))
biases2 = tf.Variable(tf.zeros([1, 10]) + 0.1,)
weight_assign_op_list.append(tf.assign(biases2, tf.placeholder(tf.float32, [1, 10])))
prediction = tf.nn.softmax(tf.matmul(output1, full_connected_layer2) + biases2)

# the error between prediction and real data
cross_entropy = tf.reduce_mean(-tf.reduce_sum(ys * tf.log(prediction + 1e-10),
                                              reduction_indices=[1]))       # loss

global_step = tf.Variable(tf.constant(0))
lr = tf.train.exponential_decay(learning_rate, global_step=global_step, decay_steps=1, decay_rate=0.9, staircase=True)

train_step = tf.train.GradientDescentOptimizer(lr).minimize(cross_entropy)

weights = tf.trainable_variables()

sess = tf.Session(config=config)
sess.run(tf.global_variables_initializer())

app = Flask(__name__)
executor = ThreadPoolExecutor(3)
client_weights = io.BytesIO()
received_client_weight = []

def update_weight():
    # print("final list: ", received_client_weight)
    total_weight = received_client_weight[0]
    if len(received_client_weight) == 1:
        # avg_weight = [each_total_weight for each_total_weight in total_weight]
        # print("final weights: ", avg_weight)
        received_client_weight.clear()
        # sess.run([tf.assign(t, e) for t, e in zip(weights, total_weight)])
        return
    for weight_index in range(1, len(received_client_weight)):
        tmp_weight = []
        this_weight = received_client_weight[weight_index]
        for i in range(len(total_weight)):
            tmp_weight.append(np.sum([total_weight[i], this_weight[i]], axis=0))
        total_weight = tmp_weight
    avg_weight = [each_total_weight / len(received_client_weight) for each_total_weight in total_weight]
    # print("final weights: ", avg_weight)
    received_client_weight.clear()
    weight_placeholder_start_index = 2;
    for w, r in zip(weight_assign_op_list, avg_weight):
        sess.run(w, feed_dict={"Placeholder_" + str(weight_placeholder_start_index) + ":0": r})
        weight_placeholder_start_index += 1

def train():
    for epoch in range(int(epoch_num / local_epoch_num)):
        for local_epoch in range(local_epoch_num):
            for iter in range(int(len(data_x) / batch_size)):
                batch_data = sess.run(batch)
                loss_val, _ = sess.run([cross_entropy, train_step], feed_dict={xs:batch_data[0], ys:batch_data[1]})
            logging.info('client {} epoch {}:loss={}'.format(this_index, epoch, loss_val))
            # logging.info('client {} epoch {}:accuracy={}'.format(this_index, epoch, sess.run(accuracy, feed_dict={xs: test_x, ys: test_y})))
            updated_weights = sess.run(weights)
            np.save(client_weights, updated_weights, allow_pickle=True)
            client_weights.seek(0)
            file = {'client_weights': client_weights}
            requests.post("http://localhost:" + select_client() + "/receive_model", files=file)
            client_weights.seek(0)
            client_weights.truncate()
            global lock
            lock.acquire()
            received_client_weight.append(updated_weights)
            update_weight()
            lock.release()

def select_client():
    return str(all_addresses[random.randint(0, len(all_addresses) - 1)])

@app.route('/start_training', methods=['POST'])
def start_training():
    training_thread = threading.Thread(target=train, daemon=True)
    training_thread.start()
    return "start training"

@app.route('/receive_model', methods=['POST'])
def receive_model():
    file = request.files.get('client_weights')
    received_weights = np.load(file, allow_pickle=True)
    global lock
    lock.acquire()
    received_client_weight.append(received_weights)
    # print("received weights: ", received_weights)
    lock.release()
    return 'continue training'

@app.route('/heart_beat', methods=['GET'])
def send_heart_beat():
    return 'alive'

app.run(port=this_address, threaded=True)