import abc
import json
import os
import threading
import time
from concurrent.futures import wait, ALL_COMPLETED
from typing import Dict, List

from flask import request

from .utils import send_data


class NodeInfo (object):
	def __init__ (self, name: str, ip: str, port: int):
		self.name: str = name
		self.ip: str = ip
		self.port: int = port


class Manager (metaclass=abc.ABCMeta):
	def __init__ (self, testbed):
		self.testbed = testbed
		self.eNode: Dict [str, NodeInfo] = {}
		self.pNode: Dict [str, NodeInfo] = {}
		self.nodeNumber: int = 0
		self.logFile: List [str] = []
		self.logFileFolder: str = ''
		self.lock = threading.RLock ()

		self.__load_default_route ()

	def load_node_info (self):
		for name, en in self.testbed.eNode.items ():
			self.eNode [name] = NodeInfo (name, en.ip, en.hostPort)
		for name, pn in self.testbed.pNode.items ():
			self.pNode [name] = NodeInfo (name, pn.ip, pn.hostPort)
		self.nodeNumber = len (self.eNode) + len (self.pNode)

	def __load_default_route (self):
		@self.testbed.flask.route ('/print', methods=['POST'])
		def route_print ():
			"""
			listen message from worker/worker_utils.py, send_print ().
			it will print the ${msg}.
			"""
			print (request.form ['msg'])
			return ''

		@self.testbed.flask.route ('/update/tc', methods=['GET'])
		def route_update_tc ():
			"""
			you can send a GET request to this /update/tc to update the
			tc settings of physical and emulated nodes.
			"""

			def update_physical_tc (_physical, _agent_port: int):
				"""
				send the tc settings to a physical node.
				this request can be received by worker/agent.py, route_physical_tc ().
				"""
				_data = {
					'NET_NODE_NIC': _physical.nic,
					'NET_NODE_TC': _physical.tc,
					'NET_NODE_TC_IP': _physical.tcIP,
					'NET_NODE_TC_PORT': _physical.tcPort
				}
				print ('update_physical_tc: send to ' + _physical.name)
				_res = send_data ('POST', '/physical/tc', _physical.ip, _agent_port,
					data={'data': json.dumps (_data)})
				if _res == '':
					print ('physical node ' + _physical.name + ' update tc succeed')
				else:
					print ('physical node ' + _physical.name + ' update tc failed, err:')
					print (_res)

			def update_emulated_tc (_data: Dict, _emulator_ip: str, _agent_port: int):
				"""
				send the tc settings to an emulator.
				this request can be received by worker/agent.py, route_emulated_tc_update ().
				"""
				print ('update_emulated_tc: send to ' + ', '.join (_data.keys ()))
				_res = send_data ('POST', '/emulated/tc/update', _emulator_ip, _agent_port,
					data={'data': json.dumps (_data)})
				_ret = json.loads (_res)
				for _name in _ret:
					if 'msg' in _ret [_name]:
						print ('emulated node ' + _name + ' update tc failed, err:')
						print (_ret [_name] ['msg'])
					else:
						print ('emulated node ' + _name + ' update tc succeed')

			filename = request.args.get ('file')
			if filename [0] != '/':
				filename = os.path.join (self.testbed.dirName, filename)

			with open (filename, 'r') as f:
				all_nodes = []
				# emulator's ip to emulated nodes in this emulator.
				emulator_ip_to_node: Dict [str, List] = {}
				links_json = json.loads (f.read ().replace ('\'', '\"'))
				for name in links_json:
					n = self.testbed.name_to_node (name)
					all_nodes.append (n)
					n.tc.clear ()
					n.tcIP.clear ()
					n.tcPort.clear ()
				self.testbed.load_link (links_json)
				for node in all_nodes:
					if node.name in self.testbed.pNode:
						self.testbed.executor.submit (update_physical_tc, node,
							self.testbed.agentPort)
					else:
						emulator_ip = node.ip
						emulator_ip_to_node.setdefault (emulator_ip, []).append (node)
				for emulator_ip in emulator_ip_to_node:
					data = {}
					for en in emulator_ip_to_node [emulator_ip]:
						data [en.name] = {
							'NET_NODE_NIC': en.nic,
							'NET_NODE_TC': en.tc,
							'NET_NODE_TC_IP': en.tcIP,
							'NET_NODE_TC_PORT': en.tcPort
						}
					self.testbed.executor.submit (update_emulated_tc, data, emulator_ip,
						self.testbed.agentPort)
			return ''

		@self.testbed.flask.route ('/emulated/stop', methods=['GET'])
		def route_emulated_stop ():
			"""
			send a stop message to emulators.
			stop emulated nodes without remove them.
			this request can be received by worker/agent.py, route_emulated_stop ().
			"""
			self.__stop_all_emulated ()
			return ''

		@self.testbed.flask.route ('/emulated/clear', methods=['GET'])
		def route_emulated_clear ():
			"""
			send a clear message to emulators.
			stop emulated nodes and remove them.
			this request can be received by worker/agent.py, route_emulated_clear ().
			"""
			self.__clear_all_emulated ()
			return ''

		@self.testbed.flask.route ('/emulated/reset', methods=['GET'])
		def route_emulated_reset ():
			"""
			send a reset message to emulators.
			remove emulated nodes, volumes and network bridges.
			this request can be received by worker/agent.py, route_emulated_reset ().
			"""
			self.__reset_all_emulated ()
			return ''

		@self.testbed.flask.route ('/physical/stop', methods=['GET'])
		def route_physical_stop ():
			"""
			send a stop message to physical nodes.
			kill the process started by above deploy_physical ().
			this request can be received by worker/agent.py, route_physical_stop ().
			"""
			self.__stop_all_physical ()
			return ''

		@self.testbed.flask.route ('/physical/clear/tc', methods=['GET'])
		def route_physical_clear_tc ():
			"""
			send a clear tc message to physical nodes.
			clear all tc settings.
			this request can be received by worker/agent.py, route_physical_clear_tc ().
			"""
			self.__clear_all_physical_tc ()
			return ''

		@self.testbed.flask.route ('/physical/clear/nfs', methods=['GET'])
		def route_physical_clear_nfs ():
			"""
			send a clear nfs message to physical nodes.
			unmount all nfs.
			this request can be received by worker/agent.py, route_physical_clear_nfs ().
			"""
			self.__clear_all_physical_nfs ()
			return ''

		@self.testbed.flask.route ('/physical/reset', methods=['GET'])
		def route_physical_reset ():
			"""
			send a reset message to physical nodes.
			kill the process started by above deploy_physical ().
			clear all tc settings.
			unmount all nfs.
			this request can be received by worker/agent.py, route_physical_reset ().
			"""
			self.__reset_all_physical ()
			return ''

		@self.testbed.flask.route ('/conf/dataset', methods=['GET'])
		def route_conf_dataset ():
			"""
			listen message from user, send dataset conf file to all nodes.
			"""
			self.__send_conf ('dataset')
			return ''

		@self.testbed.flask.route ('/conf/structure', methods=['GET'])
		def route_conf_structure ():
			"""
			listen message from user, send structure conf file to all nodes.
			"""
			self.__send_conf ('structure')
			return ''

		@self.testbed.flask.route ('/start', methods=['GET'])
		def route_start ():
			"""
			listen message from user, start dml application.
			user need to implement self.on_route_start () by extend this class.
			"""
			if self.logFileFolder == '':
				self.logFileFolder = os.path.join (self.testbed.dirName, 'dml_file/log',
					time.strftime ('%Y-%m-%d-%H-%M-%S', time.localtime (time.time ())))
			msg = self.on_route_start (request)
			# return str explicitly is necessary.
			return str (msg)

		@self.testbed.flask.route ('/finish', methods=['GET'])
		def route_finish ():
			"""
			when finished, ask node for log file.
			user need to implement self.on_route_finish () by extend this class.
			"""
			all_finished = self.on_route_finish (request)
			if all_finished:
				print ('training completed')
				os.makedirs (self.logFileFolder)
				for pn in self.pNode.values ():
					send_data ('GET', '/log', pn.ip, pn.port)
				for en in self.eNode.values ():
					send_data ('GET', '/log', en.ip, en.port)
			return ''

		@self.testbed.flask.route ('/log', methods=['POST'])
		def route_log ():
			"""
			this function can listen log files from worker/worker_utils.py, send_log ().
			log files will be saved on ${self.logFileFolder}.
			when total_number files are received, it will parse these files into pictures
			and save them on ${self.logFileFolder}/png.
			user need to implement self.parse_log_file () by extend this class.
			"""
			name = request.args.get ('name')
			print ('get ' + name + '\'s log')
			request.files.get ('log').save (os.path.join (self.logFileFolder, name + '.log'))
			with self.lock:
				self.logFile.append (name + '.log')
				if len (self.logFile) == self.nodeNumber:
					print ('log files collection completed, saved on ' + self.logFileFolder)
					full_path = os.path.join (self.logFileFolder, 'png/')
					if not os.path.exists (full_path):
						os.mkdir (full_path)
					for filename in self.logFile:
						self.parse_log_file (request, filename)
					print ('log files parsing completed, saved on ' + self.logFileFolder + '/png')
					self.logFile.clear ()
					self.testbed.executor.submit (self.__after_log)
			return ''

	def __stop_all_emulated (self):
		def stop_emulated (_emulator_ip: str, _agent_port: int):
			send_data ('GET', '/emulated/stop', _emulator_ip, _agent_port)

		tasks = []
		for s in self.testbed.emulator.values ():
			if s.eNode:
				tasks.append (self.testbed.executor.submit (stop_emulated, s.ipW, self.testbed.agentPort))
		wait (tasks, return_when=ALL_COMPLETED)

	def __clear_all_emulated (self):
		def clear_emulated (_emulator_ip: str, _agent_port: int):
			send_data ('GET', '/emulated/clear', _emulator_ip, _agent_port)

		tasks = []
		for s in self.testbed.emulator.values ():
			if s.eNode:
				tasks.append (self.testbed.executor.submit (clear_emulated, s.ipW, self.testbed.agentPort))
		wait (tasks, return_when=ALL_COMPLETED)

	def __reset_all_emulated (self):
		def reset_emulated (_emulator_ip: str, _agent_port: int):
			send_data ('GET', '/emulated/reset', _emulator_ip, _agent_port)

		tasks = []
		for s in self.testbed.emulator.values ():
			if s.eNode:
				tasks.append (self.testbed.executor.submit (reset_emulated, s.ipW, self.testbed.agentPort))
		wait (tasks, return_when=ALL_COMPLETED)

	def __stop_all_physical (self):
		def stop_physical (_physical_ip: str, _agent_port: int):
			send_data ('GET', '/physical/stop', _physical_ip, _agent_port)

		tasks = [self.testbed.executor.submit (stop_physical, p.ip, self.testbed.agentPort)
		         for p in self.testbed.pNode.values ()]
		wait (tasks, return_when=ALL_COMPLETED)
		return ''

	def __clear_all_physical_tc (self):
		def clear_physical_tc (_physical_ip: str, _agent_port: int):
			send_data ('GET', '/physical/clear/tc', _physical_ip, _agent_port)

		tasks = [self.testbed.executor.submit (clear_physical_tc, p.ip, self.testbed.agentPort)
		         for p in self.testbed.pNode.values ()]
		wait (tasks, return_when=ALL_COMPLETED)

	def __clear_all_physical_nfs (self):
		def clear_physical_nfs (_physical_ip: str, _agent_port: int):
			send_data ('GET', '/physical/clear/nfs', _physical_ip, _agent_port)

		tasks = [self.testbed.executor.submit (clear_physical_nfs, p.ip, self.testbed.agentPort)
		         for p in self.testbed.pNode.values ()]
		wait (tasks, return_when=ALL_COMPLETED)

	def __reset_all_physical (self):
		def reset_physical (_physical_ip: str, _agent_port: int):
			send_data ('GET', '/physical/reset', _physical_ip, _agent_port)

		tasks = [self.testbed.executor.submit (reset_physical, p.ip, self.testbed.agentPort)
		         for p in self.testbed.pNode.values ()]
		wait (tasks, return_when=ALL_COMPLETED)

	def __send_conf (self, conf_type: str):
		dml_file_conf = os.path.join (self.testbed.dirName, 'dml_file/conf')
		for pn in self.pNode.values ():
			file_path = os.path.join (dml_file_conf, pn.name + '_' + conf_type + '.conf')
			with open (file_path, 'r') as f:
				print ('sent ' + conf_type + ' conf to ' + pn.name)
				send_data ('POST', '/conf/' + conf_type, pn.ip, pn.port, files={'conf': f})
		for en in self.eNode.values ():
			file_path = os.path.join (dml_file_conf, en.name + '_' + conf_type + '.conf')
			with open (file_path, 'r') as f:
				print ('sent ' + conf_type + ' conf to ' + en.name)
				send_data ('POST', '/conf/' + conf_type, en.ip, en.port, files={'conf': f})

	@abc.abstractmethod
	def on_route_start (self, req: request) -> str:
		pass

	@abc.abstractmethod
	def on_route_finish (self, req: request) -> bool:
		pass

	@abc.abstractmethod
	def parse_log_file (self, req: request, filename: str):
		pass

	def __after_log (self):
		time.sleep (5)
		print ('try to stop all physical nodes')
		self.__stop_all_physical ()
		print ('try to stop all emulated nodes')
		self.__stop_all_emulated ()
