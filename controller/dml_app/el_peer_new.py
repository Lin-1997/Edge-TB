import io
import time
from flask import request
import worker_utils
import dml_utils
from role_base import Role


class ElPeer(Role):
    t_time: float
    current_round: list
    received_number: list
    received_weights: list
    layer: int

    def __init__(self, dirname: str, nn, train_path: str, test_path: str, log_file_path: str):
        super().__init__(dirname, nn, train_path, test_path, log_file_path)
        self.initial_weights = self.nn.model.get_weights()

    def _hook_after_dataset_load(self, _) -> None:
        self.executor.submit(self.perf_eval)

    def perf_eval(self):
        if self.conf['train_len'] > 0:
            s_time = time.time()
            dml_utils.train(self.nn.model, self.train_data, self.train_labels, 1, self.conf['batch_size'],
                            self.conf['train_len'])
            t_time = time.time() - s_time
            dml_utils.assign_weights(self.nn.model, self.initial_weights)
        else:
            t_time = -1.0   # not a trainer.
        path = '/perf?node=' + self.node_name + '&time=' + str(t_time) + '&size=' + str(self.nn.size)
        worker_utils.send_data('GET', path, self.ctl_addr)
        worker_utils.log(self.node_name + ': 1 epoch time=' + str(t_time))

    def _hook_handle_structure(self) -> None:
        self.current_round = [0] * len(self.conf['layer'])
        self.received_number = [0] * len(self.conf['layer'])
        self.received_weights = [[] for _ in range(len(self.conf['layer']))]

    def load_actions(self) -> None:
        super(ElPeer, self).load_actions()

        @self.app.route('/start', methods=['GET'])
        def route_start():
            _, initial_acc = dml_utils.test_on_batch(self.nn.model, self.test_data, self.test_labels,
                                                     self.conf['batch_size'])
            msg = dml_utils.log_acc(initial_acc, 0, self.conf['layer'][-1])
            worker_utils.send_print(self.ctl_addr, self.node_name + ': ' + msg)
            self.executor.submit(self.on_route_start)
            return ''

        # replace request from the upper layer node.
        @self.app.route('/replace', methods=['POST'])
        def route_replace():
            from_layer = request.form.get('layer', type=int)
            print('POST at /replace from layer ' + str(from_layer))
            weights = dml_utils.parse_weights(request.files.get('weights'))
            self.executor.submit(self.on_route_replace, weights, from_layer)
            return ''

        # combine request from the lower layer node.
        @self.app.route('/combine', methods=['POST'])
        def route_combine():
            from_layer = request.form.get('layer', type=int)
            print('POST at /combine from layer ' + str(from_layer))
            weights = dml_utils.parse_weights(request.files.get('weights'))
            self.executor.submit(self.on_route_combine, weights, from_layer)
            return ''

        # train request from the upper layer node.
        @self.app.route('/train', methods=['POST'])
        def route_train():
            print('POST at /train')
            weights = dml_utils.parse_weights(request.files.get('weights'))
            self.executor.submit(self.on_route_train, weights)
            return ''

        @self.app.route('/forward', methods=['POST'])
        def route_forward():
            print('POST at /forward')
            node = request.form['node']
            path = request.form['path']
            worker_utils.log('forward to ' + node + path)
            data = {'node': node, 'path': path, 'layer': request.form['layer']}

            # exit the route_replace () will release the file weights.
            weights = io.BytesIO()
            request.files.get('weights').save(weights)
            weights.seek(0)

            self.executor.submit(self.on_route_forward, weights, data)
            return ''

    def on_route_start(self):
        self.layer = self.conf['layer'][-1]
        nodes = self.conf['child_node'][-1]
        self.send_weights_down(self.initial_weights, nodes)

    def send_weights_down(self, weights, nodes):
        if self.layer == 2:
            send_self = dml_utils.send_weights(weights, '/train', nodes, self.conf['connect'],
                                               forward=self.conf['forward'], layer=self.layer)
            if send_self == 1:
                worker_utils.log('send self at /train')
                self.on_route_train(weights)

        elif self.layer > 2:
            send_self = dml_utils.send_weights(weights, '/replace', nodes, self.conf['connect'],
                                               forward=self.conf['forward'], layer=self.layer)
            if send_self == 1:
                worker_utils.log('send self at /replace')
                self.on_route_replace(weights, self.layer)

    def on_route_replace(self, weights, from_layer):
        self.layer = from_layer - 1
        layer_index = self.conf['layer'].index(self.layer)
        nodes = self.conf['child_node'][layer_index]
        self.send_weights_down(weights, nodes)

    def on_route_combine(self, weights, from_layer):
        self.layer = from_layer + 1
        layer_index = self.conf['layer'].index(self.layer)

        self.weights_lock.acquire()
        self.received_number[layer_index] += 1
        dml_utils.store_weights(self.received_weights[layer_index], weights,
                                self.received_number[layer_index])
        self.weights_lock.release()

        if self.received_number[layer_index] == len(self.conf['child_node'][layer_index]):
            self.combine_weights(layer_index)

    def combine_weights(self, layer_index):
        weights = dml_utils.avg_weights(self.received_weights[layer_index],
                                        self.received_number[layer_index])
        dml_utils.assign_weights(self.nn.model, weights)
        self.received_weights[layer_index].clear()
        self.received_number[layer_index] = 0
        self.current_round[layer_index] += 1

        _, acc = dml_utils.test_on_batch(self.nn.model, self.test_data, self.test_labels, self.conf['batch_size'])
        _round, layer = self.current_round[layer_index], self.conf['layer'][layer_index]
        msg = dml_utils.log_acc(acc, _round, layer)
        worker_utils.send_print(self.ctl_addr, self.node_name + ': ' + msg)

        # meet the sync of this layer, send up to combine.
        if self.current_round[layer_index] % self.conf['sync'][layer_index] == 0:
            # is the top node.
            if self.conf['father_node'][layer_index] == 'top':
                worker_utils.log('>>>>> training ended <<<<<')
                worker_utils.send_data('GET', '/finish', self.ctl_addr)
            # isn't the top node.
            else:
                send_self = dml_utils.send_weights(weights, '/combine',
                                                   self.conf['father_node'][layer_index:layer_index + 1],
                                                   self.conf['connect'], forward=self.conf['forward'], layer=self.layer)
                if send_self == 1:
                    worker_utils.log('send self at /combine')
                    self.on_route_combine(weights, self.layer)

        # haven't met the sync, send down.
        else:
            nodes = self.conf['child_node'][layer_index]
            self.send_weights_down(weights, nodes)

    def on_route_train(self, received_weights):
        dml_utils.assign_weights(self.nn.model, received_weights)
        loss_list = dml_utils.train(self.nn.model, self.train_data, self.train_labels,
                                    self.conf['epoch'], self.conf['batch_size'], self.conf['train_len'])
        # must be the lowest layer, layer_index = 0.
        self.current_round[0] += 1

        last_epoch_loss = loss_list[-1]
        msg = dml_utils.log_loss(last_epoch_loss, self.current_round[0])
        worker_utils.send_print(self.ctl_addr, self.node_name + ': ' + msg)

        latest_weights = self.nn.model.get_weights()
        send_self = dml_utils.send_weights(latest_weights, '/combine', self.conf['father_node'][:1],
                                           self.conf['connect'], forward=self.conf['forward'], layer=1)
        if send_self == 1:
            worker_utils.log('send self at /combine')
            self.on_route_combine(latest_weights, 1)

    def on_route_forward(self, weights, data):
        if data['node'] in self.conf['connect']:
            addr = self.conf['connect'][data['node']]
            dml_utils.send_weights_helper(weights, data, addr, is_forward=False)
        else:
            addr = self.conf['forward'][data['node']]
            dml_utils.send_weights_helper(weights, data, addr, is_forward=True)
        weights.seek(0)
        weights.truncate()


if __name__ == '__main__':
    import argparse
    import os
    from nns.nn_fashion_mnist import nn

    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', type=str, help='App host', default='0.0.0.0')
    parser.add_argument('-p', '--port', type=int, help='DML port', default=3333)
    args = parser.parse_args()

    dirname = os.path.abspath(os.path.dirname(__file__))
    role = ElPeer(dirname, nn,
                  os.path.join(dirname, '../dataset/FASHION_MNIST/train_data'),
                  os.path.join(dirname, '../dataset/FASHION_MNIST/test_data'),
                  os.path.abspath(os.path.join(dirname, '../dml_file/log/')))
    role.run(host=args.host, port=args.port)
