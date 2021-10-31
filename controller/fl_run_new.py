from flask import request
import ctl_utils
from controller_base import Controller
from manager_base import RuntimeManager


class FlRuntimeManager(RuntimeManager):

    def _hook_start(self):
        root = request.args.get('root', type=str)
        if not root:
            return 'Please give a correct root name\n'

        if root in self.physical_nodes:
            ip = self.physical_nodes[root]
            ctl_utils.send_data('GET', '/start', ip, self.dml_port)
        else:
            ip_port = self.emulated_nodes[root]
            ctl_utils.send_data('GET', '/start', ip_port[0], ip_port[1])

        print('start training')


if __name__ == '__main__':
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='AppConfig yaml file', required=True)
    args = parser.parse_args()

    dirname = os.path.abspath(os.path.dirname(__file__))
    controller = Controller(dirname)
    controller.init(os.path.join(dirname, args.config))
    controller.set_runtime_manager(FlRuntimeManager(dirname))
    controller.run()
