import numpy as np
from flask import request
import dml_utils
import worker_utils
from role_base import Role


class GlPeer(Role):
    peer_list: list
    current_round: int

    # override
    def _hook_handle_structure(self) -> None:
        self.current_round = 0
        self.peer_list = list(self.conf['connect'].keys())
        self.executor.submit(self.on_route_conf_s)

    def on_route_conf_s(self) -> None:
        _, initial_acc = dml_utils.test_on_batch(self.nn.model, self.test_data, self.test_labels,
                                                 self.conf['batch_size'])
        msg = dml_utils.log_acc(initial_acc, 0)
        worker_utils.send_print(self.ctl_addr, self.node_name + ': ' + msg)

    def load_actions(self) -> None:
        super(GlPeer, self).load_actions()

        @self.app.route('/start', methods=['GET'])
        def route_start():
            print('GET at /start')
            self.executor.submit(self.on_route_start)
            return ''

        @self.app.route('/gossip', methods=['POST'])
        def route_train():
            print('POST at /gossip')
            weights = dml_utils.parse_weights(request.files.get('weights'))
            self.executor.submit(self.on_route_gossip, weights)
            return ''

    def on_route_start(self):
        self.weights_lock.acquire()
        self.gossip()
        self.weights_lock.release()

    def gossip(self):
        peer = dml_utils.random_selection(self.peer_list, 1)
        worker_utils.log("gossip to " + peer[0])
        dml_utils.send_weights(self.nn.model.get_weights(), '/gossip', peer, self.conf['connect'])

    def on_route_gossip(self, received_weights):
        self.weights_lock.acquire()

        new_weights = np.add(self.nn.model.get_weights(), received_weights) / 2
        dml_utils.assign_weights(self.nn.model, new_weights)

        self.current_round += 1
        loss_list = dml_utils.train(self.nn.model, self.train_data, self.train_labels,
                                    self.conf['epoch'], self.conf['batch_size'], self.conf['train_len'])
        last_epoch_loss = loss_list[-1]
        msg = dml_utils.log_loss(last_epoch_loss, self.current_round)
        worker_utils.send_print(self.ctl_addr, self.node_name + ': ' + msg)

        _, acc = dml_utils.test_on_batch(self.nn.model, self.test_data, self.test_labels, self.conf['batch_size'])
        msg = dml_utils.log_acc(acc, self.current_round)
        worker_utils.send_print(self.ctl_addr, self.node_name + ': ' + msg)

        if self.current_round < self.conf['sync']:
            self.gossip()

        self.weights_lock.release()


if __name__ == '__main__':
    import argparse
    import os
    from nns.nn_fashion_mnist import nn

    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', type=str, help='App host', default='0.0.0.0')
    parser.add_argument('-p', '--port', type=int, help='DML port', default=3333)
    args = parser.parse_args()

    dirname = os.path.abspath(os.path.dirname(__file__))
    role = GlPeer(dirname, nn,
                  os.path.join(dirname, '../dataset/FASHION_MNIST/train_data'),
                  os.path.join(dirname, '../dataset/FASHION_MNIST/test_data'),
                  os.path.abspath(os.path.join(dirname, '../dml_file/log/')))
    role.run(host=args.host, port=args.port)
