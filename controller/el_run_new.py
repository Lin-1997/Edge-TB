import json
import os
import random
import threading
from flask import request

import ctl_utils
from controller_base import Controller
from manager_base import RuntimeManager


class ElRuntimeManager(RuntimeManager):

    def __init__(self, dirname, log_file_path: str = None, conf_file_path: str = os.path.join('dml_file', 'conf')):
        super().__init__(dirname, log_file_path, conf_file_path)

        self.perf = {}
        self.perf_lock = threading.Lock()

    def _hook_start(self):
        root = request.args.get('root', type=str, default='')
        if root == '':
            return 'Please give a correct root name\n'

        if root in self.physical_nodes:
            node = self.physical_nodes[root]
            ctl_utils.send_data('GET', '/start', node.ip, self.dml_port)
        else:
            ip_port = self.emulated_nodes[root]
            ctl_utils.send_data('GET', '/start', ip_port[0], ip_port[1])
        print('start training')

    def load_actions(self) -> None:
        super(ElRuntimeManager, self).load_actions()

        # collect the time required for 1 epoch training for each trainer in 1 layer.
        # they may help you decide how often trainers upload weights in el.
        @self.app.route('/perf', methods=['GET'])
        def route_perf():
            node = request.args.get('node')
            total_time = request.args.get('time', type=float)
            print(node + ' use ' + str(total_time))
            self.perf[node] = total_time
            if len(self.perf) == self.node_count:
                self.perf_lock.acquire()
                self.perf['size'] = request.args.get('size', type=float)
                file_path = os.path.join(dirname, 'dml_tool/perf.txt')
                with open(file_path, 'w') as f:
                    f.write(json.dumps(self.perf))
                print('performance collection completed, saved on ' + file_path)
                self.perf_lock.release()
            return ''


class ElController(Controller):

    def _init_link(self, links) -> None:
        """ This override re-defines how to process ``appConfig.links`` in appConfig-el.yml. """
        physical_nodes = list(self.net.pNode.values())
        emulated_nodes = list(self.net.eNode.values())
        for i in range(len(emulated_nodes)):
            for j in range(len(physical_nodes)):
                self.net.symmetrical_link(emulated_nodes[i], physical_nodes[j],
                                          bw=random.randint(links['min'], links['max']), unit=links['unit'])
            for j in range(i + 1, len(emulated_nodes)):
                self.net.symmetrical_link(emulated_nodes[i], emulated_nodes[j],
                                          bw=random.randint(links['min'], links['max']), unit=links['unit'])


if __name__ == '__main__':
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='AppConfig yaml file', required=True)
    args = parser.parse_args()

    dirname = os.path.abspath(os.path.dirname(__file__))
    controller = ElController(dirname)
    controller.init(os.path.join(dirname, args.config))
    controller.set_runtime_manager(ElRuntimeManager(dirname))
    controller.run()
