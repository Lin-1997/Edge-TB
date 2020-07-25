import argparse
import io
import logging
import os
import threading
from concurrent.futures.thread import ThreadPoolExecutor

from flask import Flask, request

import util
from nns import nn_lr
from values import values_g

nn = nn_lr.get_nn ()
v = values_g.get_values ()

# 启动参数获取
parser = argparse.ArgumentParser ("Gossip Learning Node Starter")
parser.add_argument ('-n', '--node_num', dest='node_num', type=int, required=True,
	help='The amount of hosts')
parser.add_argument ('-i', '--node_index', dest='node_index', type=int, required=True,
	help='The index of the current host')
parser.add_argument ('-j', '--from_index_of_data', dest='from_index_of_data', type=int, required=True,
	help='The starting index for the assigned data in training data set')
parser.add_argument ('-k', '--end_index_of_data', dest='end_index_of_data', type=int, required=True,
	help='The ending index for the assigned data in training data set')
parser.add_argument ('-e', '--epoch_num', dest='epoch_num', type=int, help='Total number of training epochs')
parser.add_argument ('-b', '--batch_size', dest='batch_size', type=int, help='The size of batch')
parser.add_argument ('-l', '--local_epoch_num', dest='local_epoch_num', type=int,
	help='Total number of local training epochs before sending weights')
args = parser.parse_args ()

# 参数处理
v ['client_num'] = args.node_num
this_index = args.node_index
if args.epoch_num:
	v ['round'] = args.epoch_num
if args.batch_size:
	v ['batch_size'] = args.batch_size
if args.local_epoch_num:
	v ['local_epoch_num'] = args.local_epoch_num
v ['start_index'] = args.from_index_of_data
v ['end_index'] = args.end_index_of_data

# Port的设置
this_port = v ['start_port'] + this_index
print ("This is node %s" % this_index)

# 生成地址列表
for client_index in range (v ['client_num']):
	v ['all_addresses'].append ('http://localhost:' + str (v ['start_port'] + client_index))

# 除本节点以外其他所有节点的地址列表
v ['other_addresses'] = v ['all_addresses'].copy ()
del v ['other_addresses'] [this_index]

# logging的设置
log_dir = 'node/log'
if not os.path.exists (log_dir):
	os.makedirs (log_dir)
logging.basicConfig (level=logging.INFO,
	filename='log/client_' + str (this_index) + '.log',
	filemode='w',
	format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')

# 模型超参数设置
nn_lr.set_train_data_batch (v ['batch_size'], v ['round'], v ['start_index'], v ['end_index'])
nn_lr.set_train_lr (v ['learning_rate'])

app = Flask (__name__)
executor = ThreadPoolExecutor (3)
client_weights = io.BytesIO ()
v ['new_weights_list_lock'] = threading.Lock ()


# 用于控制训练过程
def node_train ():
	for r in range (v ['round']):
		loss = util.train (v ['local_epoch_num'], nn ['batch_num'], nn ['sess'], nn ['batch'], nn ['loss'],
			nn ['train_step'], nn ['xs'], nn ['ys'])
		logging.info ('worker {} round {}:loss={}'.format (this_index, r, loss))
		# 更新参数
		latest_weights = nn ['sess'].run (nn ['weights'])
		list_lock = v ['new_weights_list_lock']
		list_lock.acquire ()
		v ['new_weights_list'].append (latest_weights)
		avg_weights = util.calculate_avg_weight (v ['new_weights_list'], len (v ['new_weights_list']))
		util.assignment (nn ['assign_list'], avg_weights, nn ['sess'])
		v ['new_weights_list'].clear ()
		list_lock.release ()
		other_nodes_num = v ['client_num'] - 1
		indices = util.index_random (other_nodes_num, 1.0 / float (other_nodes_num))
		util.send_weight_down_train (client_weights, avg_weights, indices, v ['other_addresses'])


@app.route ('/start_training', methods=['POST'])
def start_training ():
	training_thread = threading.Thread (target=node_train, daemon=True)
	training_thread.start ()
	return "start training"


@app.route ('/train', methods=['POST'])
def update_weights ():
	new_weights = util.parse_received_weight (request.files.get ('weights'))
	executor.submit (on_receive_weight, new_weights)
	return 'continue training'


# 把收到的参数放进new_weights_list中
def on_receive_weight (received_w):
	list_lock = v ['new_weights_list_lock']
	list_lock.acquire ()
	v ['new_weights_list'].append (received_w)
	list_lock.release ()


@app.route ('/heart_beat', methods=['GET'])
def send_heart_beat ():
	return 'alive'


app.run (host='0.0.0.0', port=this_port, threaded=True)
