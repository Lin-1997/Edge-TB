import json
import os
import subprocess as sp
from typing import List, Dict


class Node (object):
	"""
	superclass of network nodes.
	make sure your docker image and device have the
	Linux Traffic Control installed.
	it may be named iproute2 on apt and iproute on yum.
	we also recommend to install net-tools and iperf3.
	"""

	def __init__ (self, name: str, nic: str, ip: str):
		self.name: str = name
		self.nic: str = nic
		self.ip: str = ip
		self.tc: Dict [str, str] = {}  # dst name to dst bw.
		self.tcIP: Dict [str, str] = {}  # dst name to dst ip.
		self.env: Dict [str, str] = {}

	def limit_link (self, name: str, bw: str):
		assert name not in self.tc, Exception (
			self.name + ' already has a limit to ' + name)
		self.tc [name] = bw

	def limit_link_ip (self, name: str, ip: str):
		self.tcIP [name] = ip

	def add_env (self, name: str, value: str):
		self.env [name] = value

	def add_envs (self, env_dict: Dict [str, str]):
		self.env.update (env_dict)


class Device (Node):
	"""a node that represented by a physical device (e.bw_array., Raspberry Pi)."""

	def __init__ (self, name: str, nic: str, ip: str):
		super ().__init__ (name, nic, ip)
		# key: container's name, value: container's [svc_node_port1, 2, ...].
		# all nodePorts of a container share a same limit.
		self.tcPort: Dict [str, List [int]] = {}

	def limit_link_port (self, name: str, port: List [int]):
		self.tcPort [name] = port


class Container (Node):
	"""a node that simulated by a docker container."""

	def __init__ (self, name: str, nic: str, ip: str, image: str, working_dir: str,
			cmd: List [str], cpu: int, memory: str):
		"""
		:param name: pod.containers.name.
		:param nic: network interface card's name used in Linux Traffic Control.
		:param ip: ip address of its server.
		:param image: pod.containers.image in K8s.
		:param working_dir: pod.containers.workingDir in K8s.
		:param cmd: pod.containers.command in K8s.
		:param cpu: pod.containers.resources.limits.cpu in K8s.
		:param memory: pod.containers.resources.limits.memory in K8s.
		"""
		super ().__init__ (name, nic, ip)
		self.image: str = image
		self.workingDir: str = working_dir
		self.cmd: List [str] = cmd
		self.cpu: int = cpu
		self.memory: str = memory
		# pod.volumes in K8s.
		self.vHostPath: List [str] = []
		# pod.containers.volumeMounts in K8s.
		self.vMountPath: List [str] = []
		# pod.containers.ports.containerPort and service.ports.port in K8s.
		self.containerPort: List [int] = []
		# service.ports.targetPort in K8s.
		self.svcPort: List [int] = []
		# service.ports.nodePort in K8s.
		self.svcNodePort: List [int] = []

	def add_volume (self, host_path: str, mount_path: str):
		self.vHostPath.append (host_path)
		self.vMountPath.append (mount_path)

	def add_port (self, container_port: int, svc_port: int, svc_node_port: int):
		self.containerPort.append (container_port)
		self.svcPort.append (svc_port)
		self.svcNodePort.append (svc_node_port)


class ContainerServer (object):
	"""a computer that acts as a Kubernetes-Node and can deploy multiple
	 docker containers."""

	def __init__ (self, name: str, ip: str, net_ctl_address: str):
		self.name: str = name
		self.ip: str = ip
		self.netCtlAddress: str = net_ctl_address
		self.container: Dict [str, Container] = {}
		self.nodePort: Dict [int, str] = {}

	def add_container (self, name: str, nic: str, working_dir: str, cmd: List [str], image: str,
			cpu: int = 0, memory: int = 0, unit: str = 'Gi') -> Container:
		c = Container (name, nic, self.ip, image, working_dir, cmd, cpu, str (memory) + unit)
		self.container [name] = c
		return c

	def add_port (self, container: Container, container_port: int, svc_port: int = -1,
			svc_node_port: int = -1):
		"""
		:param container:
		:param container_port: pod.containers.ports.containerPort and
		service.ports.port in K8s.
		:param svc_port: service.ports.targetPort in K8s.
		:param svc_node_port: service.ports.nodePort in K8s.
		"""
		if svc_node_port != -1:
			assert svc_node_port not in self.nodePort, Exception (
				str (svc_node_port) + ' is already used by ' + self.nodePort [svc_node_port])
			assert 30000 <= svc_node_port <= 32767, Exception (
				str (svc_node_port) + ' is not in [30000, 32767]')
			self.nodePort [svc_node_port] = container.name
		if svc_port != -1:
			container.add_port (container_port, svc_port, svc_node_port)
		else:
			container.add_port (container_port, container_port, svc_node_port)

	def save_k8s_yml (self, path):
		str_yml = ''
		# svc
		for c in self.container.values ():
			if len (c.containerPort) > 0:
				str_yml = str_yml \
				          + '---\n' \
				          + 'apiVersion: v1\n' \
				          + 'kind: Service\n' \
				          + 'metadata:\n' \
				          + '  name: s-' + c.name + '\n' \
				          + 'spec:\n' \
				          + '  selector:\n' \
				          + '    label: l-p-' + c.name + '\n' \
				          + '  type: NodePort\n' \
				          + '  ports:\n'
				for i in range (len (c.containerPort)):
					str_yml = str_yml \
					          + '    - name: pt-' + c.name + '-' + str (i + 1) + '\n' \
					          + '      port: ' + str (c.containerPort [i]) + '\n' \
					          + '      targetPort: ' + str (c.svcPort [i]) + '\n'
					if c.svcNodePort [i] != -1:
						str_yml += '      nodePort: ' + str (c.svcNodePort [i]) + '\n'
		# deployment
		for c in self.container.values ():
			str_yml = str_yml \
			          + '---\n' \
			          + 'apiVersion: apps/v1\n' \
			          + 'kind: Deployment\n' \
			          + 'metadata:\n' \
			          + '  name: d-' + c.name + '\n' \
			          + 'spec:\n' \
			          + '  selector:\n' \
			          + '    matchLabels:\n' \
			          + '      label: l-p-' + c.name + '\n' \
			          + '  template:\n' \
			          + '    metadata:\n' \
			          + '      labels:\n' \
			          + '        label: l-p-' + c.name + '\n' \
			          + '    spec:\n' \
			          + '      nodeName: ' + self.name + '\n' \
			          + '      hostname: p-' + c.name + '\n'
			if len (c.vHostPath) > 0:
				str_yml += '      volumes:\n'
				for i in range (len (c.vHostPath)):
					str_yml = str_yml \
					          + '        - name: v-' + c.name + '-' + str (i + 1) + '\n' \
					          + '          hostPath:\n' \
					          + '            path: ' + c.vHostPath [i] + '\n'
			str_yml = str_yml \
			          + '      containers:\n' \
			          + '        - name: ' + c.name + '\n' \
			          + '          image: ' + c.image + '\n' \
			          + '          imagePullPolicy: Never\n' \
			          + '          workingDir: ' + c.workingDir + '\n' \
			          + '          securityContext:\n' \
			          + '            capabilities:\n' \
			          + '              add:\n' \
			          + '                - NET_ADMIN\n'
			if c.cpu != 0 or c.memory != '0Gi':
				str_yml = str_yml \
				          + '          resources:\n' \
				          + '            limits:\n'
			if c.cpu != 0:
				str_yml += '              cpu: "' + str (c.cpu) + '"\n'
			if c.memory != '0Gi':
				str_yml += '              memory: "' + c.memory + '"\n'
			if len (c.containerPort) > 0:
				str_yml += '          ports:\n'
				for i in range (len (c.containerPort)):
					str_yml += '            - containerPort: ' + str (c.containerPort [i]) + '\n'
			if c.cmd:
				str_yml += '          command: [ "' + c.cmd [0] + '"'
				for i in range (len (c.cmd) - 1):
					str_yml += ', "' + c.cmd [i + 1] + '"'
				str_yml += ' ]\n'
			str_yml = str_yml \
			          + '          env:\n' \
			          + '            - name: NET_NODE_NAME\n' \
			          + '              value: "' + c.name + '"\n' \
			          + '            - name: NET_CTL_ADDRESS\n' \
			          + '              value: "' + self.netCtlAddress + '"\n'
			for key in c.env:
				str_yml = str_yml \
				          + '            - name: ' + key + '\n' \
				          + '              value: "' + c.env [key] + '"\n'
			if len (c.vMountPath) > 0:
				str_yml += '          volumeMounts:\n'
				for i in range (len (c.vMountPath)):
					str_yml = str_yml \
					          + '            - name: v-' + c.name + '-' + str (i + 1) + '\n' \
					          + '              mountPath: ' + c.vMountPath [i] + '\n'
		# save as yml file
		yml_name = os.path.abspath (os.path.join (path, self.name + '.yml'))
		with open (yml_name, 'w')as f:
			f.writelines (str_yml)

	def deploy_k8s_yml (self, path):
		yml_path = os.path.abspath (os.path.join (path, self.name + '.yml'))
		print ('try to delete the old deployment of ' + self.name + '.yml')
		# hide the error of not found.
		sp.Popen ('kubectl delete -f ' + yml_path, stderr=sp.PIPE, shell=True).wait ()
		sp.Popen ('kubectl create -f ' + yml_path, shell=True).wait ()


class Net (object):
	def __init__ (self, address: str):
		self.address: str = address
		self.device: Dict [str, Device] = {}  # device's name to device object.
		self.containerServer: Dict [str, ContainerServer] = {}  # server's name to server object.
		self.container: Dict [str, ContainerServer] = {}  # container's name to its server object.
		self.tcLinkNumber = 0

	def add_container_server (self, name: str, ip: str) -> ContainerServer:
		assert name not in self.containerServer, Exception (name + ' is included')
		cs = ContainerServer (name, ip, self.address)
		self.containerServer [name] = cs
		return cs

	def add_device (self, name: str, nic: str, ip: str) -> Device:
		assert name not in self.device, Exception (name + ' is included')
		d = Device (name, nic, ip)
		self.device [name] = d
		return d

	def add_container (self, server: ContainerServer, name: str, nic: str, working_dir: str,
			cmd: List [str], image: str, cpu: int = 0, memory: int = 0, unit: str = 'Gi') -> Container:
		"""
		add a container to a container server.
		even if the containers are on different container servers, they cannot have the same name.
		"""
		assert name not in self.container, Exception (name + ' is in ' + self.container [name].name)
		assert unit in ['Mi', 'Gi'], Exception (unit + ' is not in ["Mi", "Gi"]')
		self.container [name] = server
		return server.add_container (name, nic, working_dir, cmd, image, cpu, memory, unit)

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
		TC can only set a approximately upper limit of the bandwidth.
		n1-----bw----->>n2
		n1<<-----no TC settings-----n2
		:param n1: the first Node.
		:param n2: the second Node.
		:param bw: bandwidth.
		:param unit: one of [kbit, mbit, gbit, kbps, mbps, gbps], i.e.,
			[Kilobits, Megabits, Gigabits, Kilobytes, Megabytes, Gigabytes] per second.
		"""
		assert unit in ['kbit', 'mbit', 'gbit', 'kbps', 'mbps', 'gbps'], Exception (
			unit + ' is not in ["kbit", "mbit", "gbit", "kbps", "mbps", "gbps"]')
		self.tcLinkNumber += 1
		if isinstance (n1, Container):
			if isinstance (n2, Container):  # n1-C, n2-C
				# for containers, they communicate through K8s service ip.
				# container's service ip can be obtained through system env
				n1.limit_link (n2.name, str (bw) + unit)
			else:  # n1-C, n2-D
				# for container, device's ip need to be declared explicitly.
				n1.limit_link (n2.name, str (bw) + unit)
				n1.limit_link_ip (n2.name, n2.ip)
		elif isinstance (n2, Device):  # n1-D, n2-D
			n1.limit_link (n2.name, str (bw) + unit)
			n1.limit_link_ip (n2.name, n2.ip)
		else:  # n1-D, n2-C
			# device can only communicate with container through the server ip.
			# there may be many containers sharing the same server ip.
			# so device needs to know container's server ip and container's nodePorts.
			n1.limit_link (n2.name, str (bw) + unit)
			n1.limit_link_ip (n2.name, n2.ip)
			n1.limit_link_port (n2.name, n2.svcNodePort)

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
		save the TC settings as txt file in json format.
		the json content can be read by the following load_bw ().
		:param path: a directory without file name.
		"""
		order = list (self.container.keys ()) + list (self.device.keys ())
		bw = []
		for name1 in order:
			node = self.name_to_node (name1)
			bw.append ([])
			for name2 in order:
				if name1 == name2:
					bw [-1].append ('inf')
				elif name2 in node.tc:
					bw [-1].append (node.tc [name2])
				else:
					bw [-1].append ('None')
		if not path:
			txt_name = os.path.abspath (os.path.join (os.path.dirname (__file__), 'bw.txt'))
		else:
			txt_name = os.path.abspath (os.path.join (path, 'bw.txt'))
		data = {'order': order, 'bw': bw}
		with open (txt_name, 'w') as f:
			f.writelines (json.dumps (data).replace ('], ', '],\n'))

	def load_bw (self, order: List [str], bw: List [List [str]]):
		"""
		:param order: what node's name does the row/column represent.
		:param bw: bandwidth between nodes.
		an example:
		order = ['n1, 'd1', 'n2']
		bw = [
		['inf', '2mbps', '3mbps'],
		['2mbps', 'inf', 'None'],
		['2mbps', '2mbps', 'inf']
		]
		"""
		for i in range (len (order)):
			n1 = self.name_to_node (order [i])
			for j in range (len (order)):
				if i == j: continue
				unit = bw [i] [j] [-4:]
				if unit == 'None': continue
				_bw = int (bw [i] [j] [:-4])
				n2 = self.name_to_node (order [j])
				self.single_link_limit (n1, n2, _bw, unit)

	def save_k8s_yml (self, path=None):
		"""
		save the deployment of containers as k8s yml files.
		:param path: a directory without file name.
		"""
		if not path:
			path = os.path.dirname (__file__)
		if not os.path.exists (path):
			os.makedirs (path)
		for cs in self.containerServer.values ():
			cs.save_k8s_yml (path)

	def deploy_k8s_yml (self, path=None):
		"""
		deploy K8s yml files.
		:param path: a directory without file name.
		"""
		if not path:
			path = os.path.dirname (__file__)
		for cs in self.containerServer.values ():
			cs.deploy_k8s_yml (path)
