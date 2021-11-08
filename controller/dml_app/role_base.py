import os
import json
import threading
import typing as t
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from flask import Flask, request
import worker_utils
import dml_utils


class Role:

    # add any extra property that should be known by worker.

    train_data: np.ndarray
    train_labels: np.ndarray

    test_data: np.ndarray
    test_labels: np.ndarray
    
    def __init__(self, dirname: str, nn: t.Any, train_path: str, test_path: str, log_file_path: str) -> None:
        self.dirname = dirname
        self.nn = nn
        """ The neural network. """
        self.input_shape = nn.input_shape

        self.ctl_addr = os.getenv('NET_CTL_ADDRESS')
        self.agent_addr = os.getenv('NET_AGENT_ADDRESS')
        self.node_name = os.getenv('NET_NODE_NAME')

        self.app = Flask(__name__)
        """ The Flask app. """
        self.executor = ThreadPoolExecutor(1)
        """ The thread pool executor. """
        self.weights_lock = threading.Lock()

        self.train_path = train_path
        self.test_path = test_path

        self.conf: dict = {}
        """ A dict storing all the configurations from controller. """

        self.log_file = os.path.join(log_file_path, self.node_name + '.log')
        worker_utils.set_log(self.log_file)

        self.load_actions()

    def load_actions(self) -> None:
        """ To add custom actions, override this function, call super first, then add routes. """
        assert self.app is not None, 'App is not ready'
        self.action_hi()
        self.action_dataset()
        self.action_structure()
        self.action_log()

    def action_hi(self) -> None:
        """ Register a heartbeat listener.
        If this node is a container, Docker will send a GET here every 30s.
        On receiving the request, send a heartbeat to the agent, if this node is a container.

        When the agent receives the heartbeat of a container for the first time, it will deploy the container's tc
        settings.

        We do not recommend changing this behavior.
        """
        @self.app.route('/hi', methods=['GET'])
        def route_hi():
            worker_utils.heartbeat(self.agent_addr, self.node_name)
            return 'this is node ' + self.node_name + '\n'

    def action_dataset(self) -> None:
        """ Action on receiving dataset configuration.
        By default it receives request from /conf/dataset and load corresponding data in another thread.

        | To only change how the dataset is loaded, override ``on_route_conf_d()`` below.
        | To perform actions after the dataset is loaded, override ``_hook_after_dataset_load()`` below.
        | To change the route behavior, simply override this function. This will invalidate the above functions.
        """
        @self.app.route('/conf/dataset', methods=['POST'])
        def route_conf_d():
            f = request.files.get('conf').read()
            self.conf.update(json.loads(f))
            print('POST at /conf/dataset')
            self.executor.submit(self.on_route_conf_d).add_done_callback(self._hook_after_dataset_load)
            return ''

    def on_route_conf_d(self):
        if self.conf.get('test_len', 0) > 0:
            self.test_data, self.test_labels = dml_utils.load_data(self.test_path, self.conf['test_start_index'],
                                                                   self.conf['test_len'], self.input_shape)
        if self.conf.get('train_len', 0) > 0:
            self.train_data, self.train_labels = dml_utils.load_data(self.train_path,
                                                                     self.conf['train_start_index'],
                                                                     self.conf['train_len'], self.input_shape)

    def _hook_after_dataset_load(self, _) -> None:
        """ Hook function after loading dataset. """
        pass

    def action_structure(self) -> None:
        """ Action on receiving structure configuration.
        By default it receives request from /conf/dataset and just saves the configuration into self.conf.

        To perform actions after saving the conf, override ``_hook_handle_structure()`` below.
        """
        @self.app.route('/conf/structure', methods=['POST'])
        def route_conf_s():
            f = request.files.get('conf').read()
            self.conf.update(json.loads(f))
            print('POST at /conf/structure')
            self._hook_handle_structure()
            return ''

    def _hook_handle_structure(self) -> None:
        """ Hook function after receiving structure conf. """
        pass

    def action_log(self) -> None:
        """ Action on receiving log request.
        By default it receives request from /log and sends back the log file.

        To change the route behavior, simply override this function (not recommended). """
        @self.app.route('/log', methods=['GET'])
        def route_log():
            self.executor.submit(self.on_route_log)
            return ''

    def on_route_log(self) -> None:
        worker_utils.send_log(self.ctl_addr, self.log_file, self.node_name)

    def run(self, host: str, port: t.Union[str, int]) -> None:
        self.app.run(host, int(port))
