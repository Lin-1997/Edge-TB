import getopt
import io
import logging
import sys
import threading
from concurrent.futures.thread import ThreadPoolExecutor

from flask import Flask, request

from . import util
from .nn import nn_lr
from .values import values_gossip

nn = nn_lr.get_nn()
v = values_gossip.get_values()

# 启动参数获取
try:
    options, args = getopt.getopt(sys.argv[1:], "n:i:e:b:l::j:k",
                                  ["client_num=", "this_index=", "epoch_num=", "batch_size=",
                                    "local_epoch_num=",  "start_data_index=", "end_data_index="])
except getopt.GetoptError:
    sys.exit()

# 预初始化该值
this_index = 0

#参数处理
for option, value in options:
    if option in ("-n", "--client_num"):
        v['client_num'] = int(value)
    if option in ("-i", "--this_index"):
        this_index = int(value)
    if option in ("-r", "--round"):
        v['round'] = int(value)
    if option in ("-b", "--batch_size"):
        v['batch_size'] = int(value)
    if option in ("-l", "--local_epoch_num"):
        v['local_epoch_num'] = int(value)
    if option in ("-j", "--start_data_index"):
        v['start_index'] = int(value)
    if option in ("-k", "--end_data_index"):
        v['end_index'] = int(value)

if len(args) > 0:
    print("error args: {0}".format(args))

# Port的设置
this_port = v['start_port'] + this_index
print("This is node %s" % this_index)
# 除本节点以外其他所有节点的地址列表
v['other_addresses'] = v['all_addresses'].copy()
del v['other_addresses'][this_index]

# logging的设置
logging.basicConfig(level=logging.INFO,
                    filename='log/client_' + str(this_index) + '.log',
                    filemode='w',
                    format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')

# 模型超参数设置
nn_lr.set_train_data_batch(v['batch_size'], v['epoch_num'])
nn_lr.set_train_lr(v['learning_rate'])

app = Flask(__name__)
executor = ThreadPoolExecutor(3)
client_weights = io.BytesIO()
v['new_weights_list_lock'] = threading.Lock()

# 用于控制训练过程
def node_train():
    for r in range(v['round']):
        loss = util.train(v['local_epoch_num'], nn['batch_num'], nn['sess'], nn['batch'], nn['loss'],
                   nn['train_step'], nn['xs'], nn['ys'])
        logging.info('worker {} round {}:loss={}'.format(this_index, r, loss))
        # 更新参数
        latest_weights = nn['sess'].run(nn['weights'])
        list_lock = v['new_weights_list_lock']
        list_lock.acquire()
        v['new_weights_list'].append(latest_weights)
        avg_weights = util.calculate_avg_weight(v['new_weights_list'], len(v['new_weights_list']))
        util.assignment(nn['assign_list'], avg_weights, nn['sess'])
        v['new_weights_list'].clear()
        list_lock.release()
        other_nodes_num = v['client_num'] - 1
        indices = util.index_random(other_nodes_num , 1.0 / float(other_nodes_num))
        util.send_weight_down(client_weights, avg_weights, indices, v['other_addresses'])


@app.route('/start_training', methods=['POST'])
def start_training():
    executor.submit(node_train)
    return "start training"


@app.route('/update_weights', methods=['POST'])
def update_weights():
    new_weights = util.parse_received_weight(request.files.get('weights'))
    executor.submit(on_receive_weight, new_weights)
    return 'continue training'

# 把收到的参数放进new_weights_list中
def on_receive_weight(received_w):
    list_lock = v['new_weights_list_lock']
    list_lock.acquire()
    v['new_weights_list'].append(received_w)
    list_lock.release()


@app.route('/heart_beat', methods=['GET'])
def send_heart_beat():
    return 'alive'

app.run(port=this_port, threaded=True)