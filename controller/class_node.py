import ipaddress
import json
import os
from typing import List, Dict

dirname = os.path.abspath (os.path.dirname (__file__))


class Node (object):
	"""
	superclass of network nodes.
	make sure your computing device and docker image have the
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


class PhysicalNode (Node):
	"""a physical node that represented by a computing device."""

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


class EmulatedNode (Node):
	"""a emulated node that represented by a docker container."""

	def __init__ (self, name: str, nic: str, emulator, image: str, working_dir: str,
			cmd: List [str], cpu: int, memory: str):
		"""
		:param name: container_name and environment:NET_NODE_NAME in yml.
		:param nic: network interface card's name used in Linux Traffic Control.
		:param emulator: the emulator it deployed on.
		:param image: image in yml.
		:param working_dir: working_dir in yml.
		:param cmd: command in yml.
		:param cpu: number of cpu used in cpuset in yml.
		:param memory: mem_limit in yml.
		"""
		super ().__init__ (name, nic, emulator.ip)
		self.emulator: Emulator = emulator
		self.image: str = image
		self.workingDir: str = working_dir
		self.cmd: List [str] = cmd
		self.cpu: int = cpu
		self.memory: str = memory
		self.volume: Dict [str, str] = {}  # host path to node path.
		self.port: Dict [int, int] = {}  # node port to host port.

	def add_volume (self, host_path: str, node_path: str):
		assert node_path [0] == '/', Exception (node_path + ' is not an absolute path')
		self.volume [host_path] = node_path

	def add_nfs (self, tag: str, node_path: str):
		assert tag in self.emulator.nfsPath, Exception (tag + ' is not mounted by emulator')
		assert node_path [0] == '/', Exception (node_path + ' is not an absolute path')
		self.volume [tag] = node_path + '/:ro'

	def add_port (self, port: int, host_port: int):
		assert port not in self.port, Exception (str (port) + ' has been used')
		assert 4000 <= host_port <= 30000, Exception (
			str (host_port) + ' is not in [4000, 30000]')
		self.emulator.add_port (host_port, self.name)
		self.port [port] = host_port


class Emulator (object):
	"""a computing device that can deploy multiple emulated nodes."""

	def __init__ (self, name: str, ip: str, net):
		self.name: str = name
		self.ip: str = ip
		self.net: Net = net
		self.nfsPath: List [str] = []  # mounted nfs tags.
		self.eNode: Dict [str, EmulatedNode] = {}  # emulated node's name to emulated node object.
		self.hostPort: Dict [int, str] = {}  # host port to emulated node's name.

	def mount_nfs (self, tag: str):
		assert tag in self.net.nfsClient, Exception (tag + ' is not shared by net')
		assert tag not in self.nfsPath, Exception (tag + ' has been mounted')
		client = ipaddress.ip_network (self.net.nfsClient [tag], strict=False)
		client_start, client_end = [x for x in client.hosts ()] [0], [x for x in client.hosts ()] [-1]
		assert client_start <= ipaddress.ip_address (self.ip) <= client_end, Exception (
			self.ip + ' is not in the subnet of ' + self.net.nfsClient [tag])
		self.nfsPath.append (tag)

	def add_node (self, name: str, nic: str, working_dir: str, cmd: List [str], image: str,
			cpu: int = 0, memory: int = 0, unit: str = 'G') -> EmulatedNode:
		assert name not in self.eNode, Exception (name + ' has been used')
		assert unit in ['M', 'G'], Exception (unit + ' is not in ["M", "G"]')
		self.net.try_add_emulated_node (name)
		en = EmulatedNode (name, nic, self, image, working_dir, cmd, cpu, str (memory) + unit)
		self.net.add_emulated_node (name, en)
		self.eNode [name] = en
		return en

	def add_port (self, host_port: int, name: str):
		assert host_port not in self.hostPort, Exception (
			str (host_port) + ' has been used by ' + self.hostPort [host_port])
		self.hostPort [host_port] = name

	def save_yml (self):
		if not self.eNode:
			return
		str_yml = 'version: "2.1"\n'
		if self.nfsPath:
			str_yml += 'volumes:\n'
			for tag in self.nfsPath:
				str_yml = str_yml \
				          + '  ' + tag + ':\n' \
				          + '    driver_opts:\n' \
				          + '      type: "nfs"\n' \
				          + '      o: "addr=' + self.net.ip + ',ro"\n' \
				          + '      device: ":' + self.net.nfsPath [tag] + '"\n'
		cpu_start = 0
		str_yml += 'services:\n'
		for en in self.eNode.values ():
			str_yml = str_yml \
			          + '  ' + en.name + ':\n' \
			          + '    container_name: ' + en.name + '\n' \
			          + '    image: ' + en.image + '\n' \
			          + '    working_dir: ' + en.workingDir + '\n' \
			          + '    stdin_open: true\n' \
			          + '    tty: true\n' \
			          + '    cap_add:\n' \
			          + '      - NET_ADMIN\n'
			# agent will change the 0xffff in NET_AGENT_ADDRESS to it's port.
			str_yml = str_yml \
			          + '    environment:\n' \
			          + '      - NET_NODE_NAME=' + en.name + '\n' \
			          + '      - NET_AGENT_ADDRESS=' + self.ip + ':0xffff\n' \
			          + '      - NET_CTL_ADDRESS=' + self.net.address + '\n'
			for key in en.env:
				str_yml += '      - ' + key + '=' + en.env [key] + '\n'
			# see controller/ctrl_run_example.py to get why it is :4444,
			# and controller/dml_app/el_peer.py to get why it is /hi.
			str_yml = str_yml \
			          + '    healthcheck:\n' \
			          + '      test: curl -f http://localhost:4444/hi\n'
			if en.volume:
				str_yml += '    volumes:\n'
				for v in en.volume:
					str_yml += '      - ' + v + ':' + en.volume [v] + '\n'
			if en.port:
				str_yml += '    ports:\n'
				for p in en.port:
					str_yml += '      - "' + str (en.port [p]) + ':' + str (p) + '"\n'
			if en.cpu != 0:
				str_yml += '    cpuset: ' + str (cpu_start) + '-' + str (cpu_start + en.cpu - 1) + '\n'
				cpu_start += en.cpu
			if en.memory != '0G':
				str_yml += '    mem_limit: ' + en.memory + '\n'
			if en.cmd:
				str_yml += '    command: ' + ' '.join (en.cmd) + '\n'

		# save as yml file
		yml_name = os.path.join (dirname, self.name + '.yml')
		with open (yml_name, 'w')as f:
			f.writelines (str_yml)


class Net (object):
	def __init__ (self, ip: str, port: int):
		self.ip: str = ip
		self.port: int = port
		self.address = ip + ':' + str (port)
		self.nfsClient: Dict [str, str] = {}  # nfs tag to nfs client ip/mask.
		self.nfsPath: Dict [str, str] = {}  # nfs tag to nfs path.
		self.pNode: Dict [str, PhysicalNode] = {}  # physical node's name to physical node object.
		self.emulator: Dict [str, Emulator] = {}  # emulator's name to emulator object.
		self.eNode: Dict [str, EmulatedNode] = {}  # emulated node's name to emulated node object.
		self.tcLinkNumber = 0

	def add_nfs (self, tag: str, ip: str, mask: int, path: str):
		assert tag not in self.nfsClient, Exception (tag + ' has been used')
		assert 0 <= mask <= 32, Exception (str (mask) + ' is not in range [0, 32]')
		assert path [0] == '/', Exception (path + ' is not an absolute path')
		self.nfsClient [tag] = ip + '/' + str (mask)
		self.nfsPath [tag] = path

	def add_emulator (self, name: str, ip: str) -> Emulator:
		assert name not in self.emulator, Exception (name + ' has been used')
		e = Emulator (name, ip, self)
		self.emulator [name] = e
		return e

	def add_physical_node (self, name: str, nic: str, ip: str) -> PhysicalNode:
		assert name not in self.pNode, Exception (name + ' has been used')
		self.pNode [name] = PhysicalNode (name, nic, ip, self)
		return self.pNode [name]

	def try_add_emulated_node (self, name: str):
		"""
		even if two emulated nodes are on different emulators, they cannot have the same name.
		"""
		assert name not in self.eNode, Exception (name + ' is in ' + self.eNode [name].emulator.name)

	def add_emulated_node (self, name: str, en: EmulatedNode):
		self.eNode [name] = en

	def save_node_ip (self):
		"""
		save the node's ip address as json file.
		we use the name "node_ip.json" in controller/dml_tool/*_structure_conf.py,
		so please do not change it.
		"""
		emulator = {}
		e_node = {}
		p_node = {}
		for e in self.emulator.values ():
			emulator [e.name] = e.ip
			e_node [e.name] = list (e.eNode.keys ())
		for pn in self.pNode.values ():
			p_node [pn.name] = pn.ip
		file_name = (os.path.join (dirname, 'node_ip.json'))
		data = {'emulator': emulator, 'emulated_node': e_node, 'physical_node': p_node}
		with open (file_name, 'w') as f:
			f.writelines (json.dumps (data, indent=2))

	def asymmetrical_link (self, n1, n2, bw: int, unit: str):
		"""
		parameters will be passed to Linux Traffic Control.
		n1-----bw----->>n2
		n1<<-----no tc settings-----n2
		:param n1: the first Node.
		:param n2: the second Node.
		:param bw: bandwidth.
		:param unit: one of [kbit, mbit, gbit, kbps, mbps, gbps], i.e.,
			[Kilobits, Megabits, Gigabits, Kilobytes, Megabytes, Gigabytes] per second.
		"""
		assert unit in ['kbit', 'mbit', 'gbit', 'kbps', 'mbps', 'gbps'], Exception (
			unit + ' is not in ["kbit", "mbit", "gbit", "kbps", "mbps", "gbps"]')
		self.tcLinkNumber += 1
		n1.limit_link (n2.name, str (bw) + unit, n2.ip)
		if not n2.name in self.pNode:  # n2 is emulated node
			n1.limit_link_port (n2.name, list (n2.port.values ()))

	def symmetrical_link (self, n1, n2, bw: int, unit: str):
		"""
		n1-----bw----->>n2
		n1<<-----bw-----n2
		they are NOT sharing a network bandwidth.
		they just happen to have the same network bandwidth.
		"""
		self.asymmetrical_link (n1, n2, bw, unit)
		self.asymmetrical_link (n2, n1, bw, unit)

	def name_to_node (self, name) -> PhysicalNode or EmulatedNode:
		"""
		get node by name.
		"""
		if name in self.pNode:
			return self.pNode [name]
		elif name in self.eNode:
			return self.eNode [name]
		else:
			Exception ('no such node called ' + name)

	def save_bw (self):
		"""
		save the tc settings as json file in json format.
		the json content can be read by the following load_bw ().
		we use the name "links.json" in controller/dml_tool/*_structure_conf.py,
		so please do not change it.
		"""
		links = {}
		for pn in self.pNode.values ():
			if not pn.tc:
				continue
			links [pn.name] = []
			for dest in pn.tc:
				links [pn.name].append ({"dest": dest, "bw": pn.tc [dest]})

		for e in self.emulator.values ():
			for en in e.eNode.values ():
				if not en.tc:
					continue
				links [en.name] = []
				for dest in en.tc:
					links [en.name].append ({"dest": dest, "bw": en.tc [dest]})

		filename = (os.path.join (dirname, 'links.json'))
		with open (filename, 'w') as f:
			f.writelines (json.dumps (links, indent=2))

	def load_bw (self, links_json):
		for name in links_json:
			src = self.name_to_node (name)
			for dest_json in links_json [name]:
				dest = self.name_to_node (dest_json ['dest'])
				unit = dest_json ['bw'] [-4:]
				_bw = int (dest_json ['bw'] [:-4])
				self.asymmetrical_link (src, dest, _bw, unit)

	def save_yml (self):
		"""
		save the deployment of emulated nodes as yml files.
		"""
		for cs in self.emulator.values ():
			cs.save_yml ()
