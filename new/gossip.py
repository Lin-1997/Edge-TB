import getopt
import io
import logging
import sys
import threading
from concurrent.futures.thread import ThreadPoolExecutor

from flask import Flask, request

from .nn.nn_lr import get_nn
from .values import values_gossip

nn = get_nn()
v = values_gossip.get_values()

# 启动参数获取
try:
    options, args = getopt.getopt(sys.argv[1:], "n:i:e:b:l::j:k", ["client_num=", "this_index=", "epoch_num=", "batch_size=",
                                                                   "local_epoch_num=",  "start_data_index=", "end_data_index="])
except getopt.GetoptError:
    sys.exit()

# 预初始化该值
this_index = 0

#参数处理
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

# logging的设置
logging.basicConfig(level=logging.INFO,
                    filename='log/client_' + str(this_index) + '.log',
                    filemode='w',
                    format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')

app = Flask(__name__)
executor = ThreadPoolExecutor(3)
client_weights = io.BytesIO()


@app.route('/start_training', methods=['POST'])
def start_training():
    return "start training"


@app.route('/receive_model', methods=['POST'])
def receive_model():
    return 'continue training'


def on_receive_weight(received_w):
    print(received_w)


@app.route('/heart_beat', methods=['GET'])
def send_heart_beat():
    return 'alive'


# app.run(port=this_address, threaded=True)