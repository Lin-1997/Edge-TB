import json
import threading
from flask import request
import numpy as np
import dml_utils
import worker_utils
from role_base import Role


class FlAggregator(Role):
    initial_weights: list
    trainers: list
    trainer_per_round: int
    current_round: int
    received_number: int
    received_weights: list

    # for customized selection >>>

    total_time: dict
    send_time: dict
    name_list: list
    prob_list: list
    prob_lock: threading.Lock

    # <<< for customized selection

    def _hook_handle_structure(self) -> None:
        self.current_round = 0
        self.received_number = 0
        self.received_weights = []
        self.trainers = self.conf['child_node']
        self.trainer_per_round = int(len(self.trainers) * self.conf['trainer_fraction'])
        self.initial_weights = self.nn.model.get_weights()

    def load_actions(self) -> None:
        super().load_actions()

        # for customized selection >>>

        self.total_time = {}
        self.send_time = {}
        self.name_list = []
        self.prob_list = []
        self.prob_lock = threading.Lock()

        @self.app.route('/ttime', methods=['GET'])
        def route_ttime():
            print('GET at /ttime')
            node = request.args.get('node')
            _time = request.args.get('time', type=float)
            print('train: ' + node + ' use ' + str(_time))
            self.total_time[node] = _time

            if len(self.total_time) == len(self.trainers):
                self.prob_lock.acquire()
                if len(self.total_time) == len(self.trainers):
                    file_path = os.path.join(dirname, '../dml_file/ttime.txt')
                    with open(file_path, 'w') as f:
                        f.write(json.dumps(self.total_time))
                        print('ttime collection completed, saved on ' + file_path)
                self.prob_lock.release()
            return ''

        @self.app.route('/stest', methods=['POST'])
        def route_stest():
            print('POST at /stest')
            # just get the weights to test the time.
            _ = dml_utils.parse_weights(request.files.get('weights'))
            return ''

        @self.app.route('/stime', methods=['GET'])
        def route_stime():
            print('GET at /stime')
            node = request.args.get('node')
            _time = request.args.get('time', type=float)
            print('send: ' + node + ' use ' + str(_time))
            self.send_time[node] = _time

            if len(self.send_time) == len(self.trainers):
                self.prob_lock.acquire()
                if len(self.send_time) == len(self.trainers):
                    file_path = os.path.join(dirname, '../dml_file/stime.txt')
                    with open(file_path, 'w') as f:
                        f.write(json.dumps(self.send_time))
                        print('stime collection completed, saved on ' + file_path)

                    count = 0
                    for node in self.total_time:
                        self.total_time[node] += self.send_time[node]
                    file_path = os.path.join(dirname, '../dml_file/totaltime.txt')
                    with open(file_path, 'w') as f:
                        f.write(json.dumps(self.total_time))
                        print('totaltime collection completed, saved on ' + file_path)
                    for node in self.total_time:
                        self.total_time[node] = 1 / (self.total_time[node] ** 0.5)
                        count += self.total_time[node]
                    for node in self.total_time:
                        self.name_list.append(node)
                        self.prob_list.append(round(self.total_time[node] / count, 3) * 1000)
                    count = 0
                    for i in range(len(self.prob_list)):
                        count += self.prob_list[i]
                    self.prob_list[-1] += 1000 - count
                    for i in range(len(self.prob_list)):
                        self.prob_list[i] /= 1000
                    print('prob_list = ')
                    print(self.prob_list)
                self.prob_lock.release()
            return ''

        # <<< for customized selection

        @self.app.route('/start', methods=['GET'])
        def route_start():
            _, initial_acc = dml_utils.test(self.nn.model, self.test_data, self.test_labels)
            msg = dml_utils.log_acc(initial_acc, 0)
            worker_utils.send_print(self.ctl_addr, self.node_name + ': ' + msg)
            self.executor.submit(self.on_route_start)
            return ''

        # combine request from the lower layer node.
        @self.app.route('/combine', methods=['POST'])
        def route_combine():
            print('POST at /combine')
            weights = dml_utils.parse_weights(request.files.get('weights'))
            self.executor.submit(self.on_route_combine, weights)
            return ''

    # for customized selection >>>

    def customized_selection(self, number):
        return np.random.choice(self.name_list, number, p=self.prob_list, replace=False)

    # <<< for customized selection

    def on_route_start(self):
        # trainers_round = dml_utils.random_selection (self.trainers, self.trainer_per_round)
        trainers_round = self.customized_selection(self.trainer_per_round)
        dml_utils.send_weights(self.initial_weights, '/train', trainers_round, self.conf['connect'])
        worker_utils.send_print(self.ctl_addr, 'start FL')

    def on_route_combine(self, weights):
        self.weights_lock.acquire()
        self.received_number += 1
        dml_utils.store_weights(self.received_weights, weights, self.received_number)
        self.weights_lock.release()

        if self.received_number == self.trainer_per_round:
            self.combine_weights()

    def combine_weights(self):
        weights = dml_utils.avg_weights(self.received_weights, self.received_number)
        dml_utils.assign_weights(self.nn.model, weights)
        self.received_weights.clear()
        self.received_number = 0
        self.current_round += 1

        _, acc = dml_utils.test(self.nn.model, self.test_data, self.test_labels)
        msg = dml_utils.log_acc(acc, self.current_round)
        worker_utils.send_print(self.ctl_addr, self.node_name + ': ' + msg)

        if self.current_round == self.conf['sync']:
            worker_utils.log('>>>>>training ended<<<<<')
            worker_utils.send_data('GET', '/finish', self.ctl_addr)
        else:  # send down to train.
            # trainers_round = dml_utils.random_selection (self.trainers, self.trainer_per_round)
            trainers_round = self.customized_selection(self.trainer_per_round)
            dml_utils.send_weights(weights, '/train', trainers_round, self.conf['connect'])


if __name__ == '__main__':
    import argparse
    import os
    from nns.nn_fashion_mnist import nn

    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', type=str, help='App host', default='0.0.0.0')
    parser.add_argument('-p', '--port', type=int, help='DML port', default=3333)
    args = parser.parse_args()

    dirname = os.path.abspath(os.path.dirname(__file__))
    role = FlAggregator(dirname, nn,
                        os.path.join(dirname, '../dataset/FASHION_MNIST/train_data'),
                        os.path.join(dirname, '../dataset/FASHION_MNIST/test_data'),
                        os.path.abspath(os.path.join(dirname, '../dml_file/log/')))
    role.run(host=args.host, port=args.port)
