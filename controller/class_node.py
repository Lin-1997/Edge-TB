import ipaddress
import json
import os
from typing import List, Dict


class Node (object):
	"""
	superclass of network nodes.
	make sure your docker image and device have the
	Linux Traffic Control installed.
	it may be named iproute2 on apt or iproute on yum.
	we also recommend to install some useful tools,
	like net-tools, iperf3, iputils-ping and nano.
	"""

	def __init__ (self, name: str, nic: str, ip: str):
		self.name: str = name
		self.nic: str = nic
		self.ip: str = ip
		self.env: Dict [str, str] = {}
		self.tc: Dict [str, str] = {}  # dst name to dst bw.
		self.tcIP: Dict [str, str] = {}  # dst name to dst ip.
		self.tcPort: Dict [str, List [int]] = {}  # dst name to dst host ports.

	def add_env (self, name: str, value: str):
		self.env [name] = value

	def add_envs (self, env_dict: Dict [str, str]):
		self.env.update (env_dict)

	def limit_link (self, name: str, bw: str, ip: str):
		assert name not in self.tc, Exception (
			self.name + ' already has a limit to ' + name)
		self.tc [name] = bw
		self.tcIP [name] = ip

	def limit_link_port (self, name: str, port: List [int]):
		self.tcPort [name] = port


class Device (Node):
	"""a node that represented by a physical device (e.g, Raspberry Pi)."""

	def __init__ (self, name: str, nic: str, ip: str, net):
		super ().__init__ (name, nic, ip)
		self.net: Net = net
		self.workingDir: str = ''
		self.cmd: List [str] = []
		self.nfsMount: Dict [str, str] = {}  # nfs path to mount point.

	def mount_nfs (self, tag: str, mount_point: str):
		assert tag in self.net.nfsClient, Exception (tag + ' is not shared by net')
		assert tag not in self.nfsMount, Exception (tag + ' has been mounted')
		client = ipaddress.ip_network (self.net.nfsClient [tag], strict=False)
		client_start, client_end = [x for x in client.hosts ()] [0], [x for x in client.hosts ()] [-1]
		assert client_start <= ipaddress.ip_address (self.ip) <= client_end, Exception (
			self.ip + ' is not in the subnet of ' + self.net.nfsClient [tag])
		self.nfsMount [self.net.nfsPath [tag]] = mount_point

	def set_cmd (self, working_dir: str, cmd: List [str]):
		assert self.workingDir == '' and not self.cmd, Exception ('cmd has been set')
		self.workingDir = working_dir
		self.cmd.extend (cmd)


class Container (Node):
	"""a node that emulated by a docker container."""

	def __init__ (self, name: str, nic: str, server, image: str, working_dir: str,
			cmd: List [str], cpu: int, memory: str):
		"""
		:param name: container_name and environment:NET_NODE_NAME in yml.
		:param nic: network interface card's name used in Linux Traffic Control.
		:param server: the container server object it deployed on.
		:param image: image in yml.
		:param working_dir: working_dir in yml.
		:param cmd: command in yml.
		:param cpu: number of cpu used in cpuset in yml.
		:param memory: mem_limit in yml.
		"""
		super ().__init__ (name, nic, server.ip)
		self.server: ContainerServer = server
		self.image: str = image
		self.workingDir: str = working_dir
		self.cmd: List [str] = cmd
		self.cpu: int = cpu
		self.memory: str = memory
		self.volume: Dict [str, str] = {}  # host path to container path.
		self.port: Dict [int, int] = {}  # container port to host port.

	def add_volume (self, host_path: str, container_path: str):
		assert container_path [0] == '/', Exception (container_path + ' is not an absolute path')
		self.volume [host_path] = container_path

	def add_nfs (self, tag: str, container_path: str):
		assert tag in self.server.nfsPath, Exception (tag + ' is not mounted by server')
		assert container_path [0] == '/', Exception (container_path + ' is not an absolute path')
		self.volume [tag] = container_path

	def add_port (self, port: int, host_port: int):
		assert port not in self.port, Exception (str (port) + ' has been used')
		assert 4000 <= host_port <= 30000, Exception (
			str (host_port) + ' is not in [4000, 30000]')
		self.server.add_port (host_port, self.name)
		self.port [port] = host_port


class ContainerServer (object):
	"""a computer that can deploy multiple docker containers."""

	def __init__ (self, name: str, ip: str, net):
		self.name: str = name
		self.ip: str = ip
		self.net: Net = net
		self.nfsPath: List [str] = []  # mounted nfs tags.
		self.container: Dict [str, Container] = {}  # container's name to container object.
		self.hostPort: Dict [int, str] = {}  # host port to container's name.

	def mount_nfs (self, tag: str):
		assert tag in self.net.nfsClient, Exception (tag + ' is not shared by net')
		assert tag not in self.nfsPath, Exception (tag + ' has been mounted')
		client = ipaddress.ip_network (self.net.nfsClient [tag], strict=False)
		client_start, client_end = [x for x in client.hosts ()] [0], [x for x in client.hosts ()] [-1]
		assert client_start <= ipaddress.ip_address (self.ip) <= client_end, Exception (
			self.ip + ' is not in the subnet of ' + self.net.nfsClient [tag])
		self.nfsPath.append (tag)

	def add_container (self, name: str, nic: str, working_dir: str, cmd: List [str], image: str,
			cpu: int = 0, memory: int = 0, unit: str = 'G') -> Container:
		assert name not in self.container, Exception (name + ' has been used')
		assert unit in ['M', 'G'], Exception (unit + ' is not in ["M", "G"]')
		self.net.add_container (name, self)
		c = Container (name, nic, self, image, working_dir, cmd, cpu, str (memory) + unit)
		self.container [name] = c
		return c

	def add_port (self, host_port: int, name: str):
		assert host_port not in self.hostPort, Exception (
			str (host_port) + ' has been used by ' + self.hostPort [host_port])
		self.hostPort [host_port] = name

	def save_yml (self, path):
		if not self.container:
			return
		str_yml = 'version: "2.1"\n'
		if self.nfsPath:
			str_yml += 'volumes:\n'
			for tag in self.nfsPath:
				str_yml = str_yml \
				          + '  ' + tag + ':\n' \
				          + '    driver_opts:\n' \
				          + '      type: nfs\n' \
				          + '      o: addr=' + self.net.ip + ',ro\n' \
				          + '      device: ":' + self.net.nfsPath [tag] + '"\n'
		cpu_start = 0
		str_yml += 'services:\n'
		for c in self.container.values ():
			str_yml = str_yml \
			          + '  ' + c.name + ':\n' \
			          + '    container_name: ' + c.name + '\n' \
			          + '    image: ' + c.image + '\n' \
			          + '    working_dir: ' + c.workingDir + '\n' \
			          + '    stdin_open: true\n' \
			          + '    tty: true\n' \
			          + '    cap_add:\n' \
			          + '      - NET_ADMIN\n'
			# agent will change the 0xffff in NET_AGENT_ADDRESS to it's port.
			str_yml = str_yml \
			          + '    environment:\n' \
			          + '      - NET_NODE_NAME=' + c.name + '\n' \
			          + '      - NET_AGENT_ADDRESS=' + self.ip + ':0xffff\n' \
			          + '      - NET_CTL_ADDRESS=' + self.net.address + '\n'
			for key in c.env:
				str_yml += '      - ' + key + '=' + c.env [key] + '\n'
			# see controller/ctrl_run_example.py to get why it is :4444,
			# and controller/dml_app/EL.py to get why it is /hi.
			str_yml = str_yml \
			          + '    healthcheck:\n' \
			          + '      test: curl -f http://localhost:4444/hi\n'
			if c.volume:
				str_yml += '    volumes:\n'
				for v in c.volume:
					str_yml += '      - ' + v + ':' + c.volume [v] + '\n'
			if c.port:
				str_yml += '    ports:\n'
				for p in c.port:
					str_yml += '      - "' + str (c.port [p]) + ':' + str (p) + '"\n'
			if c.cpu != 0:
				str_yml += '    cpuset: ' + str (cpu_start) + '-' + str (cpu_start + c.cpu - 1) + '\n'
				cpu_start += c.cpu
			if c.memory != '0G':
				str_yml += '    mem_limit: ' + c.memory + '\n'
			if c.cmd:
				str_yml += '    command: ' + ' '.join (c.cmd) + '\n'

		# save as yml file
		yml_name = os.path.abspath (os.path.join (path, self.name + '.yml'))
		with open (yml_name, 'w')as f:
			f.writelines (str_yml)


class Net (object):
	def __init__ (self, ip: str, port: int):
		self.ip: str = ip
		self.port: int = port
		self.address = ip + ':' + str (port)
		self.nfsClient: Dict [str, str] = {}  # nfs tag to nfs client ip/mask.
		self.nfsPath: Dict [str, str] = {}  # nfs tag to nfs path.
		self.device: Dict [str, Device] = {}  # device's name to device object.
		self.containerServer: Dict [str, ContainerServer] = {}  # server's name to server object.
		self.container: Dict [str, ContainerServer] = {}  # container's name to the server object it belong to.
		self.tcLinkNumber = 0

	def add_nfs (self, tag: str, ip: str, mask: int, path: str):
		assert tag not in self.nfsClient, Exception (tag + ' has been used')
		assert 0 <= mask <= 32, Exception (str (mask) + ' is not in range [0, 32]')
		assert path [0] == '/', Exception (path + ' is not an absolute path')
		self.nfsClient [tag] = ip + '/' + str (mask)
		self.nfsPath [tag] = path

	def add_container_server (self, name: str, ip: str) -> ContainerServer:
		assert name not in self.containerServer, Exception (name + ' has been used')
		cs = ContainerServer (name, ip, self)
		self.containerServer [name] = cs
		return cs

	def add_device (self, name: str, nic: str, ip: str) -> Device:
		assert name not in self.device, Exception (name + ' has been used')
		d = Device (name, nic, ip, self)
		self.device [name] = d
		return d

	def add_container (self, name: str, server: ContainerServer):
		"""
		even if two containers are on different container servers, they cannot have the same name.
		"""
		assert name not in self.container, Exception (name + ' is in ' + self.container [name].name)
		self.container [name] = server

	def save_node_ip (self, path=None):
		"""
		save the node's ip address as txt file in json format.
		an example:
		{
		"server" = {"server-1":"192.168.1.11", "server-2":"192.168.1.12"},
		"container" = {"server-1":["n1"], "server-2":["n2", "n3"]},
		"device" = {"d1":"192.168.1.13"}
		}
		:param path: a directory without file name.
		"""
		server = {}
		container = {}
		device = {}
		for s in self.containerServer.values ():
			server [s.name] = s.ip
			container [s.name] = list (s.container.keys ())
		for d in self.device.values ():
			device [d.name] = d.ip
		if not path:
			txt_name = os.path.abspath (os.path.join (os.path.dirname (__file__), 'node_ip.txt'))
		else:
			txt_name = os.path.abspath (os.path.join (path, 'node_ip.txt'))
		data = {'server': server, 'container': container, 'device': device}
		with open (txt_name, 'w') as f:
			f.writelines (json.dumps (data).replace ('}, ', '},\n'))

	def single_link_limit (self, n1, n2, bw: int, unit: str):
		"""
		parameters will be passed to Linux Traffic Control.
		n1-----bw----->>n2
		n1<<-----no tc settings-----n2
		:param n1: the first Node.
		:param n2: the second Node.
		:param bw: bandwidth.
		:param unit: one of [bit, kbit, mbit, gbit, bps, kbps, mbps, gbps], i.e.,
			[Bits, Kilobits, Megabits, Gigabits, Bytes, Kilobytes, Megabytes, Gigabytes] per second.
		"""
		assert unit in ['bit', 'kbit', 'mbit', 'gbit', 'bps', 'kbps', 'mbps', 'gbps'], Exception (
			unit + ' is not in ["bit", "kbit", "mbit", "gbit", "bps",  "kbps", "mbps", "gbps"]')
		self.tcLinkNumber += 1
		n1.limit_link (n2.name, str (bw) + unit, n2.ip)
		if not n2.name in self.device:  # n2 is container
			n1.limit_link_port (n2.name, list (n2.port.values ()))

	def dual_link_limit (self, n1, n2, bw: int, unit: str):
		"""
		n1-----bw----->>n2
		n1<<-----bw-----n2
		they are NOT sharing a network bandwidth.
		they just happen to have the same network bandwidth.
		"""
		self.single_link_limit (n1, n2, bw, unit)
		self.single_link_limit (n2, n1, bw, unit)

	def name_to_node (self, name) -> Node:
		"""
		get node by name.
		"""
		assert name in self.device or name in self.container, Exception (
			'no such node called ' + name)
		if name in self.device:
			return self.device [name]
		else:
			server = self.container [name]
			return server.container [name]

	def save_bw (self, path=None):
		"""
		save the tc settings as txt file in json format.
		the json content can be read by the following load_bw ().
		:param path: a directory without file name.
		"""
		order = list (self.container.keys ()) + list (self.device.keys ())
		bw = {}
		for name1 in order:
			node = self.name_to_node (name1)
			bw [name1] = []
			for name2 in order:
				if name1 == name2:
					bw [name1].append ('inf')
				elif name2 in node.tc:
					bw [name1].append (node.tc [name2])
				else:
					bw [name1].append ('None')
		if not path:
			txt_name = os.path.abspath (os.path.join (os.path.dirname (__file__), 'bw.txt'))
		else:
			txt_name = os.path.abspath (os.path.join (path, 'bw.txt'))
		data = {'order': order, 'bw': bw}
		with open (txt_name, 'w') as f:
			f.writelines (json.dumps (data).replace ('], ', '],\n'))

	def load_bw (self, order: List [str], bw: Dict [str, List [str]]):
		"""
		:param order: what node's name does the column represent.
		:param bw: bandwidth between nodes.
		an example:
		order = ['n1, 'd1', 'n2']
		bw = {"n1": ['inf', '2mbps', '3mbps'],
		"n2": ['2mbps', 'inf', 'None'],
		"d1": ['2mbps', '2mbps', 'inf']}
		"""
		for name1 in bw:
			n1 = self.name_to_node (name1)
			for j in range (len (order)):
				if name1 == order [j]: continue
				if bw [name1] [j] [-4:] == 'None':  # no connection.
					unit = 'bps'
					_bw = 1
				elif bw [name1] [j] [-4].isdigit ():
					unit = bw [name1] [j] [-3:]
					_bw = int (bw [name1] [j] [:-3])
				else:
					unit = bw [name1] [j] [-4:]
					_bw = int (bw [name1] [j] [:-4])
				n2 = self.name_to_node (order [j])
				self.single_link_limit (n1, n2, _bw, unit)

	def save_yml (self, path=None):
		"""
		save the deployment of containers as yml files.
		:param path: a directory without file name.
		"""
		if not path:
			path = os.path.dirname (__file__)
		if not os.path.exists (path):
			os.makedirs (path)
		for cs in self.containerServer.values ():
			cs.save_yml (path)
