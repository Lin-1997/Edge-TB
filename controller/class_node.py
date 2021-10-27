import ipaddress
import json
import os
from typing import List, Dict
import yaml


class Node(object):
    """ Superclass of network nodes.

    Make sure your computing device and docker image have the Linux Traffic Control installed.
    It may be named iproute2 on apt or iproute on yum.

    We also recommend to install some useful tools, like net-tools, iperf3, iputils-ping and nano.
    """

    def __init__(self, name: str, nic: str, ip: str):
        self.name: str = name
        self.nic: str = nic
        """ network interface card's name used in Linux Traffic Control. """
        self.ip: str = ip
        self.env: Dict[str, str] = {}

        self.tc: Dict[str, str] = {}
        """ dst name -> dst bw. """
        self.tcIP: Dict[str, str] = {}
        """ dst name -> dst ip. """
        self.tcPort: Dict[str, List[int]] = {}
        """ dst name -> dst host ports. """

    def add_env(self, name: str, value: str):
        """ Add a new environment variable. """
        self.env[name] = value

    def add_envs(self, env_dict: Dict[str, str]):
        """ Batch add (or update) of environment variables. """
        self.env.update(env_dict)

    def limit_link(self, name: str, bw: str, ip: str):
        assert name not in self.tc, self.name + ' already has a limit to ' + name
        self.tc[name] = bw
        self.tcIP[name] = ip

    def limit_link_port(self, name: str, port: List[int]):
        self.tcPort[name] = port


class PhysicalNode(Node):
    """ A physical node represents a computing device. """

    def __init__(self, name: str, nic: str, ip: str, net):
        """ You don't need to call this constructor yourself. Call ``Net.add_physical_node`` instead. """
        super().__init__(name, nic, ip)
        self.net: Net = net
        self.workingDir: str = ''
        self.cmd: List[str] = []
        self.nfsMount: Dict[str, str] = {}
        """ NFS path to mount point. """

    def mount_nfs(self, tag: str, mount_point: str):
        # TODO better naming of the function
        assert tag in self.net.nfsClient, tag + ' is not shared by net'
        assert tag not in self.nfsMount, tag + ' has been mounted'
        # Subnet check
        client = ipaddress.ip_network(self.net.nfsClient[tag], strict=False)
        client_start, client_end = [x for x in client.hosts()][0], [x for x in client.hosts()][-1]
        assert client_start <= ipaddress.ip_address(self.ip) <= client_end, \
            self.ip + ' is not in the subnet of ' + self.net.nfsClient[tag]
        self.nfsMount[self.net.nfsPath[tag]] = mount_point

    def set_cmd(self, working_dir: str, cmd: List[str]):
        assert not self.workingDir and not self.cmd, 'cmd has been set for node ' + self.name
        self.workingDir = working_dir
        self.cmd.extend(cmd)


class EmulatedNode(Node):
    """ An emulated node represents a docker container. """

    def __init__(self, name: str, nic: str, emulator, image: str, working_dir: str,
                 cmd: List[str], cpu: int, memory: str):
        """ You don't need to call this constructor yourself. Call ``Emulator.add_node()`` instead. """
        super().__init__(name, nic, emulator.ip)
        self.emulator: Emulator = emulator
        """ The emulator it deployed on. """
        self.image: str = image
        """ The image to use (``image`` in yml). """
        self.workingDir: str = working_dir
        """ Working directory (``working_dir`` in yml). """
        self.cmd: List[str] = cmd
        """ ``command`` in yml. """
        self.cpu: int = cpu
        """ Number of cpus used in ``cpuset`` in yml. """
        self.memory: str = memory
        """ Memory limit (``mem_limit`` in yml). """
        self.volume: Dict[str, str] = {}
        """ Volumes: host path or tag -> node path. """
        self.port: Dict[int, int] = {}
        """ Port mapping: node port -> host port. """

    def add_volume(self, host_path: str, node_path: str):
        """ Add extra volume mounted to the emulator's host. The host path will be used as the tag. """
        assert node_path[0] == '/', Exception(node_path + ' is not an absolute path')
        self.volume[host_path] = node_path

    def add_nfs(self, tag: str, node_path: str):
        """ Add an nfs mount to the emulated node as a volume.

        The ``tag`` must have been mounted to the emulator (``Emulator.mount_nfs ()``).
        """
        assert tag in self.emulator.nfsPath, Exception(tag + ' is not mounted by emulator')
        assert node_path[0] == '/', Exception(node_path + ' is not an absolute path')
        self.volume[tag] = node_path + '/:ro'

    def add_port(self, port: int, host_port: int):
        """ Add a port mapping. """
        assert port not in self.port, Exception(str(port) + ' has been used')
        assert 4000 <= host_port <= 30000, Exception(str(host_port) + ' is not in [4000, 30000]')
        self.emulator.add_port(host_port, self.name)
        self.port[port] = host_port


class Emulator(object):
    """ A computing device that can deploy multiple emulated nodes. """

    def __init__(self, name: str, ip: str, net):
        self.name: str = name
        self.ip: str = ip
        self.net: Net = net
        self.nfsPath: List[str] = []
        """ Mounted nfs tags. """
        self.eNode: Dict[str, EmulatedNode] = {}
        """ emulated node's name -> EmulatedNode object. """
        self.hostPort: Dict[int, str] = {}
        """ host port -> emulated node's name. """

    def mount_nfs(self, tag: str):
        """ Mount an nfs folder to the emulated node.

        The ``tag`` must have been registered in the ``net`` it belongs to, and the emulator must be
        in the subnet specified by the tag.
        """
        assert tag in self.net.nfsClient, Exception(tag + ' is not shared by net')
        assert tag not in self.nfsPath, Exception(tag + ' has been mounted')
        client = ipaddress.ip_network(self.net.nfsClient[tag], strict=False)
        client_start, client_end = [x for x in client.hosts()][0], [x for x in client.hosts()][-1]
        assert client_start <= ipaddress.ip_address(self.ip) <= client_end, Exception(
            self.ip + ' is not in the subnet of ' + self.net.nfsClient[tag])
        self.nfsPath.append(tag)

    def add_node(self, name: str, nic: str, working_dir: str, cmd: List[str], image: str,
                 cpu: int = 0, memory: int = 0, unit: str = 'G') -> EmulatedNode:
        """
        Add a new emulated node.

        :param name: name of the emulated node,
            also `container_name` and `environment:NET_NODE_NAME` in yml.
        :param nic: network interface card's name used in Linux Traffic Control.
        :param working_dir: the emulated node's working directory.
        :param cmd: the command to execute for the emulated node.
        :param image: the image to be used.
        :param cpu: number of cpus to be used.
        :param memory: amount of memory available. set to 0 for no limit.
        :type memory: must be an integer.
        :param unit: unit of available memory.
        :type unit: either 'M' or 'G'.
        :return: the emulated node created.
        """
        assert name not in self.eNode, Exception(name + ' has been used')
        assert unit in ['M', 'G'], Exception(unit + ' is not in ["M", "G"]')
        self.net.try_add_emulated_node(name)
        en = EmulatedNode(name, nic, self, image, working_dir, cmd, cpu, str(memory) + unit)
        self.net.add_emulated_node(name, en)
        self.eNode[name] = en
        return en

    def add_port(self, host_port: int, name: str):
        """ Register a port mapping from host to the emulated node. Should be called by an ``EmulatedNode``. """
        assert host_port not in self.hostPort, \
            str(host_port) + ' has been used by ' + self.hostPort[host_port]
        self.hostPort[host_port] = name

    def save_yml(self, target: str, filename: str = None):
        f"""
        Save the emulator's configurations into a Docker Compose yml file.

        :param target: the target folder to save yml file.
        :param filename: if not specified, will use {self.name}.yml.
        """
        if not self.eNode:
            return
        compose_data = {'version': '2.1'}
        if self.nfsPath:
            compose_data['volumes'] = {}
            for tag in self.nfsPath:
                compose_data['volumes'][tag] = {
                    'driver_opts': {
                        'type': 'nfs',
                        'o': 'addr=' + self.net.ip + ',ro',
                        'device': ':' + self.net.nfsPath[tag]
                    }
                }
        cpu_start = 0
        compose_data['services'] = {}
        for en in self.eNode.values():
            service = compose_data['services'][en.name] = {
                'container_name': en.name,
                'image': en.image,
                'working_dir': en.workingDir,
                'stdin_open': True,
                'tty': True,
                'cap_add': ['NET_ADMIN'],
                'environment': [
                    'NET_NODE_NAME=' + en.name,
                    # agent will change the 0xffff in NET_AGENT_ADDRESS to it's port.
                    "NET_AGENT_ADDRESS=" + self.ip + ':0xffff',
                    "NET_CTL_ADDRESS=" + self.net.address
                ]
            }
            for key in en.env:
                service['environment'].append('key=' + en.env[key])
            # TODO 4444 and /hi
            heartbeat_url = 'http://localhost:' + list(en.port.values())[0] + '/hi'
            service['healthcheck'] = {'test': 'curl -f ' + heartbeat_url}
            if en.volume:
                service['volumes'] = []
                for v in en.volume:
                    service['volumes'].append(v + ':' + en.volume[v])
            if en.port:
                service['ports'] = []
                for p in en.port:
                    service['ports'].append(str(en.port[p]) + ':' + str(p))
            if en.cpu != 0:
                service['cpuset'] = str(cpu_start) + '-' + str(cpu_start + en.cpu - 1)
                cpu_start += en.cpu
            if en.memory[0] != '0':
                service['mem_limit'] = en.memory
            if en.cmd:
                service['command'] = ' '.join(en.cmd)

        # save as yml file
        yml_filename = os.path.join(target, (filename or self.name) + '.yml')
        with open(yml_filename, 'w') as f:
            yaml.safe_dump(compose_data, f, default_flow_style=False)


class Net(object):
    def __init__(self, ip: str, port: int):
        self.ip: str = ip
        self.port: int = port
        self.address = ip + ':' + str(port)
        f""" {self.ip}:{self.port} """
        self.nfsClient: Dict[str, str] = {}
        """ nfs tag -> nfs client ip/mask. """
        self.nfsPath: Dict[str, str] = {}
        """ nfs tag -> nfs path. """
        self.pNode: Dict[str, PhysicalNode] = {}
        """ physical node's name -> PhysicalNode object. """
        self.emulator: Dict[str, Emulator] = {}
        """ emulator's name -> Emulator object. """
        self.eNode: Dict[str, EmulatedNode] = {}
        """ emulated node's name -> EmulatedNode object. """
        self.tcLinkNumber = 0
        """ Total number of tc links (connections). """

    def add_nfs(self, tag: str, ip: str, mask: int, path: str):
        """
        Add an nfs mount.

        :param tag: as identifier as well as Docker Compose volume tags.
        :param ip: the subnet that the mount is available to.
        :param mask: subnet mask.
        :param path: the path on the (controller) host.
        """
        assert tag not in self.nfsClient, Exception(tag + ' has been used')
        assert 0 <= mask <= 32, Exception(str(mask) + ' is not in range [0, 32]')
        assert path[0] == '/', Exception(path + ' is not an absolute path')
        self.nfsClient[tag] = ip + '/' + str(mask)
        self.nfsPath[tag] = path

    def add_emulator(self, name: str, ip: str) -> Emulator:
        """ Create and add a new emulator.

        Note that the name of the emulator has no effect on the emulated nodes' names. It is mainly
        used for dict key indexing.
        """
        assert name not in self.emulator, Exception(name + ' has been used')
        e = self.emulator[name] = Emulator(name, ip, self)
        return e

    def add_physical_node(self, name: str, nic: str, ip: str) -> PhysicalNode:
        """ Create and add a new physical node. """
        assert name not in self.pNode, Exception(name + ' has been used')
        p = self.pNode[name] = PhysicalNode(name, nic, ip, self)
        return p

    def try_add_emulated_node(self, name: str):
        """ Even if two emulated nodes are on different emulators, they cannot have the same name.

        If the name for a new node violates the restriction, an Exception is thrown.
        """
        assert name not in self.eNode, Exception(name + ' is in ' + self.eNode[name].emulator.name)

    def add_emulated_node(self, name: str, en: EmulatedNode):
        """ Register an emulated node to the net.

        Should be called by an ``Emulator`` on new node creation.
        """
        self.eNode[name] = en

    def save_node_ip(self, target):
        """
        Save the nodes' ip address (and host ports for emulated nodes) as json file.

        :param target: the target filename (should be an absolute path).
        """
        emulators = {}
        p_node = {}
        for e in self.emulator.values():
            e_nodes = {}
            for name, node in e.eNode.items():
                e_nodes[name] = [e.ip] + list(node.port.values())
            emulators[e.name] = e_nodes
        for pn in self.pNode.values():
            p_node[pn.name] = pn.ip
        file_name = target
        data = {'emulator': emulators, 'physical_node': p_node}
        with open(file_name, 'w') as f:
            f.writelines(json.dumps(data, indent=2))

    def asymmetrical_link(self, n1, n2, bw: int, unit: str):
        """
        Add an asymmetrical link to the net.

        | parameters will be passed to Linux Traffic Control.
        | n1 -----bw----->> n2
        | n1 <<-----no tc settings----- n2

        :param n1: the first Node.
        :param n2: the second Node.
        :param bw: bandwidth.
        :type bw: should be integer.
        :param unit: one of [kbit, mbit, gbit, kbps, mbps, gbps], i.e.,
            [Kilobits, Megabits, Gigabits, Kilobytes, Megabytes, Gigabytes] per second.
        """
        assert unit in ['kbit', 'mbit', 'gbit', 'kbps', 'mbps', 'gbps'], \
            unit + ' is not in ["kbit", "mbit", "gbit", "kbps", "mbps", "gbps"]'
        self.tcLinkNumber += 1
        n1.limit_link(n2.name, str(bw) + unit, n2.ip)
        if n2.name not in self.pNode:  # n2 is emulated node
            n1.limit_link_port(n2.name, list(n2.port.values()))

    def symmetrical_link(self, n1, n2, bw: int, unit: str):
        """
        Add two asymmetrical links to the net.

        | n1 -----bw----->> n2
        | n1 <<-----bw----- n2
        | They are NOT sharing a network bandwidth.
        | They just happen to have the same network bandwidth.

        :param n1: the first Node.
        :param n2: the second Node.
        :param bw: bandwidth.
        :type bw: should be integer.
        :param unit: one of [kbit, mbit, gbit, kbps, mbps, gbps], i.e.,
            [Kilobits, Megabits, Gigabits, Kilobytes, Megabytes, Gigabytes] per second.
        """
        self.asymmetrical_link(n1, n2, bw, unit)
        self.asymmetrical_link(n2, n1, bw, unit)

    def get_node_by_name(self, name) -> PhysicalNode or EmulatedNode:
        if name in self.pNode:
            return self.pNode[name]
        elif name in self.eNode:
            return self.eNode[name]
        else:
            raise Exception('no such node called ' + name)

    def save_bw(self, target):
        """
        Save the tc settings as json file in json format.
        The json content can be read by the following ``load_bw ()``.

        :param target: the target filename (should be an absolute path).
        """
        links = {}
        for pn in self.pNode.values():
            if not pn.tc:
                continue
            links[pn.name] = []
            for dest in pn.tc:
                links[pn.name].append({"dest": dest, "bw": pn.tc[dest]})

        for e in self.emulator.values():
            for en in e.eNode.values():
                if not en.tc:
                    continue
                links[en.name] = []
                for dest in en.tc:
                    links[en.name].append({"dest": dest, "bw": en.tc[dest]})

        filename = target
        with open(filename, 'w') as f:
            f.writelines(json.dumps(links, indent=2))

    def load_bw(self, links_json):
        """
        Load the net's tc settings from a file.

        :param links_json: the filename of the tc settings json.
        """
        with open(links_json, 'r') as f:
            links = json.loads(f.read().replace('\'', '\"'))

        for name in links:
            src = self.get_node_by_name(name)
            for dest_json in links[name]:
                dest = self.get_node_by_name(dest_json['dest'])
                unit = dest_json['bw'][-4:]
                _bw = int(dest_json['bw'][:-4])
                self.asymmetrical_link(src, dest, _bw, unit)

    def save_yml(self, target):
        """
        Save the deployment of emulated nodes as yml files.

        :param target: target folder.
        """
        for cs in self.emulator.values():
            cs.save_yml(target)
