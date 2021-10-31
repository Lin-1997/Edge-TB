import time
from flask import request
import dml_utils
import worker_utils
from role_base import Role


class FlTrainer(Role):

    current_round: int

    def _hook_handle_structure(self) -> None:
        # for customized selection >>>
        self.executor.submit(self.perf_eval)
        # <<< for customized selection
        self.current_round = 0

    # for customized selection >>>

    def perf_eval(self) -> None:
        s = time.time()
        dml_utils.train(self.nn.model, self.train_data, self.train_labels, 1,
                        self.conf['batch_size'], self.conf['train_len'])
        e = time.time() - s
        addr = self.conf['connect'][self.conf['father_node'][0]]
        path = '/ttime?node=' + self.node_name + '&time=' + str(e)
        worker_utils.log(self.node_name + ': train time=' + str(e))
        worker_utils.send_data('GET', path, addr)

        s = time.time()
        dml_utils.send_weights(self.nn.model.get_weights(), '/stest', self.conf['father_node'], self.conf['connect'])
        e = time.time() - s
        path = '/stime?node=' + self.node_name + '&time=' + str(e)
        worker_utils.log(self.node_name + ': send time=' + str(e))
        worker_utils.send_data('GET', path, addr)

    # <<< for customized selection

    def load_actions(self) -> None:
        super().load_actions()

        @self.app.route('/train', methods=['POST'])
        def on_route_train():
            print('POST at /train')
            weights = dml_utils.parse_weights(request.files.get('weights'))
            self.executor.submit(self.on_route_train, weights)
            return ''

    def on_route_train(self, received_weights):
        dml_utils.assign_weights(self.nn.model, received_weights)
        loss_list = dml_utils.train(self.nn.model, self.train_data, self.train_labels,
                                    self.conf['epoch'], self.conf['batch_size'], self.conf['train_len'])
        self.current_round += 1

        last_epoch_loss = loss_list[-1]
        msg = dml_utils.log_loss(last_epoch_loss, self.current_round)
        worker_utils.send_print(self.ctl_addr, self.node_name + ': ' + msg)
        dml_utils.send_weights(self.nn.model.get_weights(), '/combine', self.conf['father_node'], self.conf['connect'])


if __name__ == '__main__':
    import argparse
    import os
    from nns.nn_fashion_mnist import nn

    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', type=str, help='App host', default='0.0.0.0')
    parser.add_argument('-p', '--port', type=int, help='DML port', default=3333)
    args = parser.parse_args()

    dirname = os.path.abspath(os.path.dirname(__file__))
    role = FlTrainer(dirname, nn,
                     os.path.join(dirname, '../dataset/FASHION_MNIST/train_data'),
                     os.path.join(dirname, '../dataset/FASHION_MNIST/test_data'),
                     os.path.abspath(os.path.join(dirname, '../dml_file/log/')))
    role.run(host=args.host, port=args.port)
