import json
import os
import subprocess as sp
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from typing import Dict, IO

import requests
from flask import request

from class_node import Net, Emulator, PhysicalNode

# this port number should be the same as the one defined in worker/agent.py.
agent_port = 3333
executor = ThreadPoolExecutor ()
tc_number = 0
tc_lock = threading.Lock ()
log_name = []
log_lock = threading.Lock ()
dirname = os.path.abspath (os.path.dirname (__file__))


def read_json (filename):
	with open (os.path.join (dirname, filename), 'r') as f:
		return json.loads (f.read ().replace ('\'', '\"'))


def send_data (method: str, path: str, address: str, port: int = None,
		data: Dict [str, str] = None, files: Dict [str, IO] = None) -> str:
	"""
	send a request to http://${address/path} or http://${ip:port/path}.
	@param method: 'GET' or 'POST'.
	@param path:
	@param address: ip:port if ${port} is None else only ip.
	@param port: only used when ${address} is only ip.
	@param data: only used in 'POST'.
	@param files: only used in 'POST'.
	@return: response.text
	"""
	if port:
		address += ':' + str (port)
	if method.upper () == 'GET':
		res = requests.get ('http://' + address + '/' + path)
		return res.text
	elif method.upper () == 'POST':
		res = requests.post ('http://' + address + '/' + path, data=data, files=files)
		return res.text
	else:
		return 'err method ' + method


def restore_nfs ():
	"""
	restore nfs to system settings.
	"""
	cmd = 'sudo exportfs -r'
	sp.Popen (cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait ()


def export_nfs (net: Net):
	"""
	export the path through nfs.
	"""
	for tag in net.nfsClient:
		client = net.nfsClient [tag]
		path = net.nfsPath [tag]
		# export the path.
		cmd = 'sudo exportfs ' + client + ':' + path
		sp.Popen (cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait ()
		# check result.
		cmd = 'sudo exportfs -v'
		p = sp.Popen (cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
		msg = p.communicate () [0].decode ()
		assert path in msg and client in msg, Exception (
			'share ' + path + ' to ' + client + ' failed')


def print_listener (app):
	@app.route ('/print', methods=['POST'])
	def route_print ():
		"""
		this function can listen message from worker/worker_utils.py, send_print ().
		it will print the ${msg}.
		"""
		print (request.form ['msg'])
		return ''


def clear_nfs_listener (app):
	@app.route ('/clear/nfs', methods=['POST'])
	def route_clear_nfs ():
		"""
		this function can listen command from user.
		restore nfs to system settings.
		"""
		cmd = 'sudo exportfs -r'
		sp.Popen (cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait ()
		return ''


def docker_tc_listener (app, net: Net):
	@app.route ('/docker/tc', methods=['POST'])
	def route_docker_tc ():
		"""
		this function can listen message from worker/agent.py, deploy_docker_tc ().
		it will save the result of deploying docker tc settings.
		"""
		global tc_number
		data = json.loads (request.form ['data'])
		number = data ['number']
		name = data ['name']
		if number == '-1':
			msg = data ['msg']
			print ('emulated node ' + name + ' tc failed, err:')
			print (msg)
		else:
			print ('emulated node ' + name + ' tc succeed')
			tc_lock.acquire ()
			tc_number += int (number)
			if tc_number == net.tcLinkNumber:
				print ('tc finish')
			tc_lock.release ()
		return ''


def send_docker_address (net: Net):
	"""
	send ctl's ${ip:port} to emulators.
	this request can be received by worker/agent.py, route_docker_address ().
	"""
	for emulator in net.emulator.values ():
		print ('send_docker_address: send to ' + emulator.name)
		send_data ('GET', '/docker/address?address=' + net.address,
			emulator.ip, agent_port)


def send_docker_tc (net: Net):
	"""
	send the tc settings to emulators.
	this request can be received by worker/agent.py, route_docker_tc ().
	"""
	for emulator in net.emulator.values ():
		data = {}
		# collect tc settings of each emulated node in this emulator.
		for e in emulator.eNode.values ():
			data [e.name] = {
				'NET_NODE_NIC': e.nic,
				'NET_NODE_TC': e.tc,
				'NET_NODE_TC_IP': e.tcIP,
				'NET_NODE_TC_PORT': e.tcPort
			}
		# the agent in emulator will deploy all tc settings of its emulated nodes.
		print ('send_docker_tc: send to ' + emulator.name)
		send_data ('POST', '/docker/tc', emulator.ip, agent_port,
			data={'data': json.dumps (data)})


def deploy_dockerfile (net: Net, tag: str, path1: str, path2: str):
	"""
	send the Dockerfile and pip requirements.txt to the agent of emulators.
	this request can be received by worker/agent.py, route_docker_build ().
	@param net:
	@param tag: docker image name:version.
	@param path1: path of Dockerfile.
	@param path2: path of pip requirements.txt.
	@return:
	"""
	tasks = [executor.submit (deploy_dockerfile_helper, s, tag, path1, path2)
	         for s in net.emulator.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def deploy_dockerfile_helper (emulator: Emulator, tag: str, path1: str, path2: str):
	with open (path1, 'r') as f1, open (path2, 'r') as f2:
		print ('deploy_dockerfile: send to ' + emulator.name)
		res = send_data ('POST', '/docker/build', emulator.ip, agent_port,
			data={'tag': tag}, files={'Dockerfile': f1, 'dml_req': f2})
		if res == '1':
			print (emulator.name + ' build image succeed')
		else:
			print (emulator.name + ' build image failed')


def deploy_all_yml (net: Net):
	"""
	send the yml files to the agent of emulators.
	this request can be received by worker/agent.py, route_docker_start ().
	"""
	tasks = []
	for s in net.emulator.values ():
		if s.eNode:
			tasks.append (executor.submit (deploy_yml, s, dirname))
	wait (tasks, return_when=ALL_COMPLETED)


def deploy_yml (emulator: Emulator, path: str):
	with open (os.path.join (path, emulator.name + '.yml'), 'r') as f:
		print ('deploy_all_yml: send to ' + emulator.name)
		send_data ('POST', '/docker/start', emulator.ip, agent_port, files={'yml': f})


def docker_controller_listener (app, net: Net):
	"""
	this function can listen command from user.
	it can controller emulated nodes.
	"""

	@app.route ('/docker/stop', methods=['GET'])
	def route_docker_stop ():
		stop_all_docker (net)
		return ''

	@app.route ('/docker/clear', methods=['GET'])
	def route_docker_clear ():
		clear_all_docker (net)
		return ''

	@app.route ('/docker/reset', methods=['GET'])
	def route_docker_reset ():
		reset_all_docker (net)
		return ''


def stop_all_docker (net: Net):
	"""
	send a stop message to emulators.
	stop emulated nodes without remove them.
	this request can be received by worker/agent.py, route_docker_stop ().
	"""
	tasks = []
	for s in net.emulator.values ():
		if s.eNode:
			tasks.append (executor.submit (stop_docker, s.ip))
	wait (tasks, return_when=ALL_COMPLETED)


def stop_docker (emulator_ip: str):
	send_data ('GET', '/docker/stop', emulator_ip, agent_port)


def clear_all_docker (net: Net):
	"""
	send a clear message to emulators.
	stop emulated nodes and remove them.
	this request can be received by worker/agent.py, route_docker_clear ().
	"""
	tasks = []
	for s in net.emulator.values ():
		if s.eNode:
			tasks.append (executor.submit (clear_docker, s.ip))
	wait (tasks, return_when=ALL_COMPLETED)


def clear_docker (emulator_ip: str):
	send_data ('GET', '/docker/clear', emulator_ip, agent_port)


def reset_all_docker (net: Net):
	"""
	send a reset message to emulators.
	remove emulated nodes, volumes and network bridges.
	this request can be received by worker/agent.py, route_docker_reset ().
	"""
	tasks = []
	for s in net.emulator.values ():
		if s.eNode:
			tasks.append (executor.submit (reset_docker, s.ip))
	wait (tasks, return_when=ALL_COMPLETED)


def reset_docker (emulator_ip: str):
	send_data ('GET', '/docker/reset', emulator_ip, agent_port)


def send_device_nfs (net: Net):
	"""
	send the nfs settings to physical nodes.
	this request can be received by worker/agent.py, route_device_nfs ().
	"""
	tasks = [executor.submit (send_device_nfs_helper, p, net.ip)
	         for p in net.pNode.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def send_device_nfs_helper (device: PhysicalNode, ip: str):
	data = {'ip': ip, 'nfs': device.nfsMount}
	print ('send_device_nfs: send to ' + device.name)
	res = send_data ('POST', '/device/nfs', device.ip, agent_port,
		data={'data': json.dumps (data)})
	err = json.loads (res)
	if not err:
		print ('device ' + device.name + ' mount nfs succeed')
	else:
		print ('device ' + device.name + ' mount nfs failed, err:')
		print (err)


def send_device_tc (net: Net):
	"""
	send the tc settings to physical nodes.
	this request can be received by worker/agent.py, route_device_tc ().
	"""
	global tc_number
	for p in net.pNode.values ():
		if not p.tc:
			print ('device ' + p.name + ' tc succeed')
			continue
		data = {
			'NET_NODE_TC': p.tc,
			'NET_NODE_TC_IP': p.tcIP,
			'NET_NODE_TC_PORT': p.tcPort
		}
		print ('device_tc_update: send to ' + p.name)
		res = send_data ('POST', '/device/tc', p.ip, agent_port,
			data={'data': json.dumps (data)})
		if res == '1':
			print ('device ' + p.name + ' tc succeed')
			tc_lock.acquire ()
			tc_number += len (p.tc)
			if tc_number == net.tcLinkNumber:
				print ('tc finish')
			tc_lock.release ()
		else:
			print ('device ' + p.name + ' tc failed, err:')
			print (res)


def send_device_env (net: Net):
	"""
	send the env to physical nodes.
	this request can be received by worker/agent.py, route_device_env ().
	"""
	for p in net.pNode.values ():
		data = {
			'NET_CTL_ADDRESS': net.address,
			'NET_AGENT_IP': p.ip,
			'NET_NODE_NIC': p.nic,
			'NET_NODE_NAME': p.name,
			'NET_NODE_ENV': p.env,
		}
		print ('send_device_env: send to ' + p.name)
		send_data ('POST', '/device/env', p.ip, agent_port,
			data={'data': json.dumps (data)})


def sent_device_req (net: Net, path: str):
	"""
	send the dml_req.txt to physical nodes.
	this request can be received by worker/agent.py, route_device_req ().
	"""
	tasks = [executor.submit (sent_device_req_helper, p, path)
	         for p in net.pNode.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def sent_device_req_helper (device: PhysicalNode, path: str):
	with open (path, 'r')as f:
		print ('sent_device_req: send to ' + device.name)
		res = send_data ('POST', '/device/req', device.ip, agent_port,
			files={'dml_req': f})
		if res == '1':
			print ('device ' + device.name + ' req succeed')
		else:
			print ('device ' + device.name + ' req failed, err:')
			print (res)


def deploy_all_device (net: Net):
	"""
	send a start message to physical nodes.
	this request can be received by worker/agent.py, route_device_start ().
	"""
	tasks = [executor.submit (deploy_device, p) for p in net.pNode.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def deploy_device (device: PhysicalNode):
	data = {'dir': device.workingDir, 'cmd': device.cmd}
	send_data ('POST', '/device/start', device.ip, agent_port,
		data={'data': json.dumps (data)})


def device_controller_listener (app, net: Net):
	"""
	this function can listen command from user.
	it can controller physical nodes.
	"""

	@app.route ('/device/stop', methods=['GET'])
	def route_device_stop ():
		stop_all_device (net)
		return ''

	@app.route ('/device/clear/tc', methods=['GET'])
	def route_device_clear_tc ():
		clear_all_device_tc (net)
		return ''

	@app.route ('/device/clear/nfs', methods=['GET'])
	def route_device_clear_nfs ():
		clear_all_device_nfs (net)
		return ''

	@app.route ('/device/reset', methods=['GET'])
	def route_device_reset ():
		reset_all_device (net)
		return ''


def stop_all_device (net: Net):
	"""
	send a stop message to physical nodes.
	kill the process started by above deploy_device ().
	this request can be received by worker/agent.py, route_device_stop ().
	"""
	tasks = [executor.submit (stop_device, p.ip) for p in net.pNode.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def stop_device (device_ip: str):
	send_data ('GET', '/device/stop', device_ip, agent_port)


def clear_all_device_tc (net: Net):
	"""
	send a clear tc message to physical nodes.
	clear all tc settings.
	this request can be received by worker/agent.py, route_device_clear_tc ().
	"""
	tasks = [executor.submit (clear_device_tc, p.ip) for p in net.pNode.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def clear_device_tc (device_ip: str):
	send_data ('GET', '/device/clear/tc', device_ip, agent_port)


def clear_all_device_nfs (net: Net):
	"""
	send a clear nfs message to physical nodes.
	unmount all nfs.
	this request can be received by worker/agent.py, route_device_clear_nfs ().
	"""
	tasks = [executor.submit (clear_device_nfs, p.ip) for p in net.pNode.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def clear_device_nfs (device_ip: str):
	send_data ('GET', '/device/clear/nfs', device_ip, agent_port)


def reset_all_device (net: Net):
	"""
	send a reset message to physical nodes.
	kill the process started by above deploy_device ().
	clear all tc settings.
	unmount all nfs.
	this request can be received by worker/agent.py, route_device_reset ().
	"""
	tasks = [executor.submit (reset_device, p.ip) for p in net.pNode.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def reset_device (device_ip: str):
	send_data ('GET', '/device/reset', device_ip, agent_port)


def update_tc_listener (app, net: Net):
	@app.route ('/update/tc', methods=['GET'])
	def route_update_tc ():
		"""
		this function can listen command from user.
		it can update the tc settings of emulated and/or physical nodes.
		"""
		print ('update tc start at ' + str (time.time ()))
		filename = request.args.get ('file')
		if filename [0] != '/':
			filename = os.path.join (dirname, filename)

		with open (filename, 'r') as f:
			all_nodes = []
			emulator_to_node = {}  # emulator to emulated nodes in this emulator.
			links_json = json.loads (f.read ().replace ('\'', '\"'))
			for name in links_json:
				n = net.name_to_node (name)
				all_nodes.append (n)
				n.tc.clear ()
				n.tcIP.clear ()
				n.tcPort.clear ()
			net.load_bw (links_json)
			for node in all_nodes:
				if node.name in net.pNode:
					executor.submit (update_device_tc, node)
				else:
					emulator = node.emulator
					emulator_to_node.setdefault (emulator, []).append (node)
			update_docker_tc (emulator_to_node)
		return ''


def update_device_tc (device):
	data = {
		'NET_NODE_TC': device.tc,
		'NET_NODE_TC_IP': device.tcIP,
		'NET_NODE_TC_PORT': device.tcPort
	}
	print ('update_device_tc: send to ' + device.name)
	res = send_data ('POST', '/device/tc/update', device.ip, agent_port,
		data={'data': json.dumps (data)})
	print (device.name + ' update tc end at ' + str (time.time ()))
	if res == '1':
		print ('physical node ' + device.name + ' update tc succeed')
	else:
		print ('physical node ' + device.name + ' update tc failed, err:')
		print (res)


def update_docker_tc (emulator_to_node):
	for emulator in emulator_to_node:
		data = {}
		for e in emulator_to_node [emulator]:
			data [e.name] = {
				'NET_NODE_NIC': e.nic,
				'NET_NODE_TC': e.tc,
				'NET_NODE_TC_IP': e.tcIP,
				'NET_NODE_TC_PORT': e.tcPort
			}
		executor.submit (update_docker_tc_helper, data, emulator)


def update_docker_tc_helper (data, emulator):
	print ('update_docker_tc: send to ' + emulator.name)
	res = send_data ('POST', '/docker/tc/update', emulator.ip, agent_port,
		data={'data': json.dumps (data)})
	print (emulator.name + ' update tc end at ' + str (time.time ()))
	ret = json.loads (res)
	for name in ret:
		if ret [name] ['number'] == '-1':
			print ('emulated node ' + emulator.name + ': ' + name + ' update tc failed, err:')
			print (ret [name] ['msg'])
		else:
			print ('emulated node ' + emulator.name + ': ' + name + ' update tc succeed')
