import os
import re
import random
import threading
from typing import Any, Dict, Union, List
from yaml import load, Loader
from flask import Flask

import ctl_utils
from class_node import Net, Node, Emulator


class Controller:
    """ Using an appConfig prototype. """

    from manager_base import RuntimeManager

    app_config: Any
    __attrs = {'localIP': 'ip', 'port': 'port', 'dmlPort': 'dml_port', 'agentPort': 'agent_port'}

    app: Flask
    net: Net
    manager: RuntimeManager

    def __init__(self, dirname: str, ip: str = None, port: int = None, dml_port: int = None, agent_port: int = None,
                 log_file_path: str = None) -> None:
        self.dirname = dirname
        self.ip, self.port, self.dml_port, self.agent_port, self.log_file_path \
            = ip, port, dml_port, agent_port, log_file_path
        self._nDict: Dict[str, Node] = {}
        self.__config_files = {}
        self.__initialized = False

        self.tc_lock = threading.Lock()
        self.tc_number = 0

    def init(self, app_config_file: Union[str, dict] = '') -> None:
        """ Initialize by reading an appConfig yaml file. """

        if type(app_config_file) == str:
            with open(app_config_file, 'r') as f:
                self.app_config = load(f, Loader=Loader)['appConfig']
        else:
            self.__config_files = app_config_file

        self.init_general(self.__load_config_part('general'))
        self.net = Net(self.ip, self.port)
        self.app = Flask(__name__)

        self.init_net(self.__load_config_part('hosts'), self.__load_config_part('nodes'))
        self.init_emulators(self.__load_config_part('emulator'))
        self.init_physical(self.__load_config_part('physical'))
        self.init_link(self.__load_config_part('links'))
        self.init_nfs(self.__load_config_part('nfs'))
        self.init_listeners()

        self.net.save_node_ip(os.path.join(self.dirname, 'node_ip.json'))
        self.net.save_bw(os.path.join(self.dirname, 'links.json'))
        self.net.save_yml(self.dirname)
        self.__initialized = True

    def init_general(self, general_config: dict) -> None:
        """ Initialize the general configurations such as IP, port, etc. Override this function for manual config. """
        for attr in self.__attrs:
            if attr in general_config and not getattr(self, self.__attrs[attr], None):
                setattr(self, self.__attrs[attr], general_config[attr])

    def init_net(self, hosts: dict, nodes: dict) -> None:
        """ Initialize the network structure. Override this function for custom initialization (e.g. by code). """
        for node_host, spec in nodes.items():
            host = hosts[spec['host']]
            cmd = self._parse_cmd(spec['cmd']) if 'cmd' in spec else []
            if spec['type'] == 'physical':
                node = self.net.add_physical_node(name=node_host, nic=host['nic'], ip=host['ip'])
                node.set_cmd(working_dir='dml_app', cmd=cmd)
                self._nDict[node_host] = node
            elif spec['type'] == 'emulator':
                emulator = self.net.add_emulator(spec['host'], host['ip'])
                if 'docker' in spec:
                    self._init_net_docker_help(node_host, emulator, spec['docker'], cmd)
                elif 'dockerGroups' in spec:
                    for group_name in spec['dockerGroups']:
                        self._init_net_docker_help(node_host + '-' + group_name, emulator,
                                                   spec['dockerGroups'][group_name], cmd)
                else:
                    raise Exception('No container spec defined')
            else:
                raise Exception('Unsupported host type')

    def _parse_cmd(self, cmd: str) -> List[str]:
        cmd_l = cmd.split(' ')
        for i in range(0, len(cmd_l)):
            if cmd_l[i][0] == '$':
                cmd_l[i] = str(getattr(self, self.__attrs[cmd_l[i][1:]]))
        return cmd_l

    def _init_net_docker_help(self, root_name: str, emulator: Emulator, docker_spec, cmd_global: list):
        ports = ctl_utils.generate_ports(docker_spec['ports'], docker_spec['containers'])
        memory, memory_unit = int(docker_spec['memory'][:-1]), docker_spec['memory'][-1]
        cmd = self._parse_cmd(docker_spec['cmd']) if 'cmd' in docker_spec else cmd_global
        if not cmd:
            raise Exception('No command for emulated nodes: ' + root_name)
        for i in range(0, docker_spec['containers']):
            node_name = root_name + '-' + str(i + 1)
            node = emulator.add_node(node_name, docker_spec['nic'], '/home/worker/dml_app', cmd,
                                     docker_spec['image'], cpu=docker_spec['cpu'],
                                     memory=memory, unit=memory_unit)
            node.add_port(self.dml_port, ports[i])
            for _, volume in docker_spec['volumes'].items():
                node.add_volume(volume['hostPath'], volume['nodePath'])
            self._nDict[node_name] = node

    def init_emulators(self, emulator_spec):
        """ Initialize emulators (e.g. build images) and register listeners. """
        if emulator_spec:
            docker_spec = emulator_spec.get('images')
            if docker_spec:
                emulator_images = {}
                for e_name in self.net.emulator:
                    emulator_images[e_name] = set()
                    for e_node in self.net.emulator[e_name].eNode.values():
                        emulator_images[e_name].add(e_node.image)
                for spec in docker_spec.values():
                    spec['dockerfile'] = os.path.join(self.dirname, spec['dockerfile'])
                    spec['requirements'] = os.path.join(self.dirname, spec['requirements'])
                ctl_utils.deploy_dockerfile(self, docker_spec, emulator_images)
        ctl_utils.send_address_to_emulator_agent(self)
        ctl_utils.docker_tc_listener(self)

    def init_physical(self, phy_spec):
        """ Initialize physical nodes and register listeners. """
        if phy_spec:
            req_spec = phy_spec.get('requirements')
            if type(req_spec) == str:
                path_req = os.path.join(self.dirname, req_spec)
                ctl_utils.sent_device_req(self, path_req)
        ctl_utils.send_device_env(self)

    def init_link(self, links) -> None:
        """ Initialize the tc links and send tc to all worker machines.
        For custom initialization, override ``_init_link()`` instead of this one.
        """
        self._init_link(links)

        if self.net.tcLinkNumber > 0:
            ctl_utils.send_docker_tc(self)
            ctl_utils.send_device_tc(self)
        else:
            print('tc finish')

    def _init_link(self, links):
        """ Initialize the tc links. Override this function for custom initialization (e.g. by code). """
        if type(links) == str:
            links_json = os.path.join(self.dirname, links)
            self.net.load_bw(links_json)
        else:  # list of link rules
            node_names = self._nDict.keys()
            for rule in links:
                rule_p = rule.split(' ')
                from_list = list(filter(lambda x: re.match(rule_p[0], x) is not None, node_names))
                to_list = list(filter(lambda x: re.match(rule_p[1], x) is not None, node_names))
                random.shuffle(from_list)
                p = 2
                conf = {'bw_min': -1, 'bw_max': -1, 'bw_rule': 'random', 'link_max': len(to_list),
                        'unit': 'mbps', 'symmetrical': False}
                while p < len(rule_p):
                    if rule_p[p] == 'random':
                        conf['bw_min'] = int(rule_p[p + 1])
                        conf['bw_max'] = int(rule_p[p + 2])
                        conf['unit'] = rule_p[p + 3]
                        p += 4
                    elif rule_p[p] == 'max':
                        conf['link_max'] = int(rule_p[p + 1])
                        p += 2
                    elif rule_p[p] == 'symmetrical':
                        conf['symmetrical'] = True
                        p += 1
                    else:
                        try:
                            conf['bw_max'] = conf['bw_min'] = int(rule_p[p])
                            conf['unit'] = rule_p[p + 1]
                            p += 2
                        except ValueError:
                            raise Exception('Link parse error')
                for i in range(0, len(from_list)):
                    node_from = self._nDict[from_list[i]]
                    random.shuffle(to_list)
                    for j in range(0, conf['link_max']):
                        node_to = self._nDict[to_list[j]]
                        if node_from.name == node_to.name:
                            continue
                        if conf['symmetrical'] and node_from.name not in node_to.tc \
                                and node_to.name not in node_from.tc:
                            self.net.symmetrical_link(node_from, node_to,
                                                      bw=random.randint(conf['bw_min'], conf['bw_max']),
                                                      unit=conf['unit'])
                        elif not conf['symmetrical'] and node_to.name not in node_from.tc:
                            self.net.asymmetrical_link(node_from, node_to,
                                                       bw=random.randint(conf['bw_min'], conf['bw_max']),
                                                       unit=conf['unit'])

    def init_nfs(self, nfs_spec: dict) -> None:
        """ Initialize the NFS mounting settings. Override this function for custom initialization or path. """
        subnet = nfs_spec.get('subnet')
        ip, mask = subnet.split('/')
        self.net.add_nfs(tag='dataset', ip=ip, mask=int(mask), path=os.path.join(self.dirname, 'dataset'))
        self.net.add_nfs(tag='dml_app', ip=ip, mask=int(mask), path=os.path.join(self.dirname, 'dml_app'))
        ctl_utils.restore_nfs()
        ctl_utils.export_nfs(self.net)

        # config nfs for all nodes
        for physical_node in self.net.pNode.values():
            physical_node.mount_nfs(tag='dml_app', mount_point='./dml_app')
            physical_node.mount_nfs(tag='dataset', mount_point='./dataset')
        for emulator in self.net.emulator.values():
            emulator.mount_nfs('dml_app')
            emulator.mount_nfs('dataset')
            for _, node in emulator.eNode.items():
                node.add_nfs('dml_app', '/home/worker/dml_app')
                node.add_nfs('dataset', '/home/worker/dataset')

        ctl_utils.clear_nfs_listener(self)
        ctl_utils.send_device_nfs(self)

    def init_listeners(self) -> None:
        ctl_utils.print_listener(self)
        ctl_utils.update_tc_listener(self)
        ctl_utils.docker_controller_listener(self)
        ctl_utils.device_controller_listener(self)

    def __load_config_part(self, part_name):
        if part_name in self.__config_files:
            with open(self.__config_files[part_name], 'r') as f:
                config = load(f, Loader=Loader)['appConfig'].get(part_name)
        else:
            config = self.app_config.get(part_name)
        return config

    def set_runtime_manager(self, manager: RuntimeManager) -> None:
        """ Set the runtime manager working with the controller. """
        self.manager = manager
        self.manager.link_controller(self)
        self.manager.load_node_ip(os.path.join(self.dirname, 'node_ip.json'))
        self.manager.load_actions()

    def run(self) -> None:
        """ Run the controller. """
        if not self.__initialized:
            raise Exception('The controller is not initialized!')
        ctl_utils.deploy_all_device(self)
        ctl_utils.deploy_all_yml(self)
        self.app.run('0.0.0.0', self.port, threaded=True)
