import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import matplotlib.pyplot as plt
from flask import Flask, request

import ctl_utils
from class_node import Net


class RuntimeManager:

    node_count: int = 0
    """ Total number of nodes (physical + emulated). """

    physical_nodes: dict = {}
    """ A dict mapping physical nodes' name to their corresponding ip+port. """

    emulated_nodes: dict = {}
    """ A dict mapping emulated nodes' name to their corresponding [ip, port]. """

    net: Net
    app: Flask

    dirname: str = ''
    """ Absolute path of the current working folder. """

    dml_port: int

    def __init__(self, dirname: str = None, log_file_path: str = None, conf_file_path: str = os.path.join('dml_file', 'conf')):
        self.dirname = dirname or os.path.abspath(os.path.dirname(__file__))
        self.executor = ThreadPoolExecutor(1)
        self.log_name = []
        self.log_lock = threading.Lock()
        self.log_file_path = ''
        self.set_log_file_path(log_file_path)
        self.conf_file_path: str = ''
        self.set_conf_file_path(conf_file_path)
        self.controller = None

    def set_log_file_path(self, log_file_path):
        if not log_file_path:
            return
        if log_file_path[0] == '/':
            self.log_file_path = log_file_path
        else:
            self.log_file_path = os.path.join(self.dirname, log_file_path)

    def set_conf_file_path(self, conf_file_path):
        if conf_file_path[0] == '/':
            self.conf_file_path = conf_file_path
        else:
            self.conf_file_path = os.path.join(self.dirname, conf_file_path)

    def link_controller(self, controller):
        """ Link to a controller. """
        self.controller = controller
        self.app = controller.app
        self.net = controller.net
        self.dml_port = controller.dml_port

    def load_node_ip(self, filename):
        node_ip = {}
        if filename[0] != '/':
            filename = os.path.join(self.dirname, filename)
        with open(filename, 'r') as file:
            node_ip.update(json.loads(file.read()))

        self.physical_nodes.update(node_ip['physical_node'])
        self.node_count = len(self.physical_nodes)
        for _, nodes in node_ip['emulator'].items():
            self.emulated_nodes.update(nodes)
            self.node_count += len(nodes)

    def load_actions(self) -> None:
        """ To add custom actions, override this function, call super first, then add routes. """
        assert self.app is not None, 'App is not ready'
        assert self.node_count > 0, 'Node ip not loaded'
        self.action_conf()
        self.action_start()
        self.action_finish()
        self.action_log()

    def action_conf(self) -> None:
        """ Send the conf file to the corresponding node. """
        @self.app.route('/conf', methods=['GET'])
        def route_conf():
            conf_type = request.args.get('type', type=int)
            if conf_type == 1:
                self.executor.submit(self._on_route_conf, 'dataset')
                return ''
            elif conf_type == 2:
                self.executor.submit(self._on_route_conf, 'structure')
                return ''
            else:
                return 'error type'

    def _on_route_conf(self, conf_type):
        for name, ip in self.physical_nodes.items():
            file_path = os.path.join(self.dirname, self.conf_file_path, name + '_' + conf_type + '.conf')
            with open(file_path, 'r') as f:
                print('sent ' + conf_type + ' conf to ' + name)
                ctl_utils.send_data('POST', '/conf/' + conf_type, ip, self.dml_port, files={'conf': f})

        for name, ip_port in self.emulated_nodes.items():
            file_path = os.path.join(self.dirname, self.conf_file_path, name + '_' + conf_type + '.conf')
            with open(file_path, 'r') as f:
                print('sent ' + conf_type + ' conf to ' + name)
                ctl_utils.send_data('POST', '/conf/' + conf_type, ip_port[0], ip_port[1], files={'conf': f})

    def action_start(self) -> None:
        @self.app.route('/start', methods=['GET'])
        def route_start():
            if not self.log_file_path:
                self.log_file_path = os.path.join(self.dirname, 'dml_file/log',
                                                  time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time())))
            
            return self._hook_start() or ''

    def _hook_start(self):
        """ Start the training process. The default is to send a /start to all nodes.
        Override this if you want different strategy (e.g. send only to a root node).
        Request data sent to controller /start is still available as the global flask.request.
        """
        for _, ip in self.physical_nodes.items():
            ctl_utils.send_data('GET', '/start', ip, self.dml_port)
        for _, ip_port in self.emulated_nodes.items():
            ctl_utils.send_data('GET', '/start', ip_port[0], ip_port[1])

        print('start training')

    def action_finish(self) -> None:
        @self.app.route('/finish', methods=['GET'])
        def route_finish():
            return self._hook_finish() or ''

    def _hook_finish(self) -> None:
        """ Action for finish.
        By default it will ask all nodes for log files.
        """
        print('training completed')
        # create a folder to save the log files of nodes.
        self.send_log_request()

    def send_log_request(self) -> None:
        os.makedirs(self.log_file_path)
        for _, ip in self.physical_nodes.items():
            ctl_utils.send_data('GET', '/log', ip, self.dml_port)
        for _, ip_port in self.emulated_nodes.items():
            ctl_utils.send_data('GET', '/log', ip_port[0], ip_port[1])

    def action_log(self) -> None:
        @self.app.route('/log', methods=['POST'])
        def route_log():
            """
            this function can listen log files from worker/worker_utils.py, send_log ().
            log files will be saved on ${log_file_path}.
            when total_number files are received, it will parse these files into pictures
            and save them on ${log_file_path}/png.
            """
            name = request.args.get('name')
            print('get ' + name + '\'s log')
            request.files.get('log').save(os.path.join(self.log_file_path, name + '.log'))
            self.log_lock.acquire()
            self.log_name.append(name + '.log')
            if len(self.log_name) == self.node_count:
                print('log files collection completed, saved on ' + self.log_file_path)
                full_path = os.path.join(self.log_file_path, 'png/')
                if not os.path.exists(full_path):
                    os.mkdir(full_path)
                for filename in self.log_name:
                    self._parse_log(self.log_file_path, filename)
                print('log files parsing completed, saved on ' + self.log_file_path + '/png')
                self.log_name.clear()
                self.executor.submit(self._after_log)
            self.log_lock.release()
            return ''

    def _after_log(self):
        time.sleep(5)
        print('try to stop all physical nodes')
        ctl_utils.stop_all_device(self.controller)
        print('try to clear all emulated nodes')
        ctl_utils.stop_all_docker(self.controller)

    # noinspection PyMethodMayBeStatic
    def _parse_log(self, path: str, filename: str):
        """
        parse log files into pictures.
        the log files format comes from worker/worker_utils.py, log_acc () and log_loss ().
        Aggregate: accuracy=0.8999999761581421, round=1,
        Train: loss=0.2740592360496521, round=1,
        we left a comma at the end for easy positioning and extending.
        """
        acc_str = 'accuracy='
        loss_str = 'loss='
        acc_list = []
        loss_list = []
        with open(os.path.join(path, filename), 'r') as f:
            for line in f:
                if line.find('Aggregate') != -1:
                    acc_start_i = line.find(acc_str) + len(acc_str)
                    acc_end_i = line.find(',', acc_start_i)
                    acc = float(line[acc_start_i:acc_end_i])
                    acc_list.append(acc)
                elif line.find('Train') != -1:
                    loss_start_i = line.find(loss_str) + len(loss_str)
                    loss_end_i = line.find(',', loss_start_i)
                    loss = float(line[loss_start_i:loss_end_i])
                    loss_list.append(loss)
        name = filename[:filename.find('.log')]
        if acc_list:
            plt.plot(acc_list, 'go')
            plt.plot(acc_list, 'r')
            plt.xlabel('round')
            plt.ylabel('accuracy')
            plt.ylim(0, 1)
            plt.title('Accuracy')
            plt.savefig(os.path.join(path, 'png/', name + '-acc.png'))
            plt.cla()
        if loss_list:
            upper = loss_list[0] * 1.2
            plt.plot(loss_list, 'go')
            plt.plot(loss_list, 'r')
            plt.xlabel('round')
            plt.ylabel('loss')
            plt.ylim(0, upper)
            plt.title('Loss')
            plt.savefig(os.path.join(path, 'png/', name + '-loss.png'))
            plt.cla()
