import json
import os
import subprocess as sp
import threading
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from typing import Dict, IO

import requests
from flask import request

from class_node import Net, ContainerServer, Device

# this port number should be the same as the one defined in worker/agent.py.
agent_port = 3333
executor = ThreadPoolExecutor (4)
tc_number = 0
tc_lock = threading.Lock ()
log_name = []
log_lock = threading.Lock ()
dirname = os.path.abspath (os.path.dirname (__file__))


def read_json (filename: str):
	with open (filename, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


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


def export_nfs (net: Net):
	"""
	export the path through nfs.
	"""
	for tag in net.nfsClient:
		client = net.nfsClient [tag]
		path = net.nfsPath [tag]
		# restore to system settings.
		cmd = 'sudo exportfs -r'
		sp.Popen (cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait ()
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
			print ('container ' + name + ' tc failed, err:')
			print (msg)
		else:
			print ('container ' + name + ' tc succeed')
			tc_lock.acquire ()
			tc_number += int (number)
			if tc_number == net.tcLinkNumber:
				print ('tc finish')
			tc_lock.release ()
		return ''


def send_docker_address (net: Net):
	"""
	send ctl's ${ip:port} to container servers.
	this request can be received by worker/agent.py, route_docker_address ().
	"""
	for server in net.containerServer.values ():
		print ('send_docker_address: send to ' + server.name)
		send_data ('GET', '/docker/address?address=' + net.address,
			server.ip, agent_port)


def send_docker_tc (net: Net):
	"""
	send the tc settings to container servers.
	this request can be received by worker/agent.py, route_docker_tc ().
	"""
	for server in net.containerServer.values ():
		data = {}
		# collect tc settings of each container in this container server.
		for c in server.container.values ():
			data [c.name] = {
				'NET_NODE_NIC': c.nic,
				'NET_NODE_TC': c.tc,
				'NET_NODE_TC_IP': c.tcIP,
				'NET_NODE_TC_PORT': c.tcPort
			}
		# the agent in container server will deploy all tc settings of its containers.
		print ('send_docker_tc: send to ' + server.name)
		send_data ('POST', '/docker/tc', server.ip, agent_port,
			data={'data': json.dumps (data)})


def deploy_dockerfile (net: Net, tag: str, path1: str, path2: str):
	"""
	send the Dockerfile and pip requirements.txt to the agent of container servers.
	this request can be received by worker/agent.py, route_docker_build ().
	@param net:
	@param tag: docker image name:version.
	@param path1: path of Dockerfile.
	@param path2: path of pip requirements.txt.
	@return:
	"""
	tasks = [executor.submit (deploy_dockerfile_helper, s, tag, path1, path2)
	         for s in net.containerServer.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def deploy_dockerfile_helper (server: ContainerServer, tag: str, path1: str, path2: str):
	with open (path1, 'r') as f1, open (path2, 'r') as f2:
		print ('deploy_dockerfile: send to ' + server.name)
		res = send_data ('POST', '/docker/build', server.ip, agent_port,
			data={'tag': tag}, files={'Dockerfile': f1, 'dml_req': f2})
		if res == '1':
			print (server.name + ' build image succeed')
		else:
			print (server.name + ' build image failed')


def deploy_all_yml (net: Net, path: str):
	"""
	send the yml files to the agent of container servers.
	this request can be received by worker/agent.py, route_docker_start ().
	"""
	tasks = [executor.submit (deploy_yml, s, path) for s in net.containerServer.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def deploy_yml (server: ContainerServer, path: str):
	with open (os.path.join (path, server.name + '.yml'), 'r') as f:
		print ('deploy_all_yml: send to ' + server.name)
		send_data ('POST', '/docker/start', server.ip, agent_port, files={'yml': f})


def docker_controller_listener (app, net: Net):
	"""
	this function can listen command from user.
	it can controller containers.
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
	send a stop message to container servers.
	stop containers without remove them.
	this request can be received by worker/agent.py, route_docker_stop ().
	"""
	for s in net.containerServer.values ():
		if s.container:
			stop_docker (s.ip)


def stop_docker (server_ip: str):
	send_data ('GET', '/docker/stop', server_ip, agent_port)


def clear_all_docker (net: Net):
	"""
	send a clear message to container servers.
	stop containers and remove them.
	this request can be received by worker/agent.py, route_docker_clear ().
	"""
	for s in net.containerServer.values ():
		if s.container:
			clear_docker (s.ip)


def clear_docker (server_ip: str):
	send_data ('GET', '/docker/clear', server_ip, agent_port)


def reset_all_docker (net: Net):
	"""
	send a reset message to container servers.
	remove containers, volumes and network bridges.
	this request can be received by worker/agent.py, route_docker_reset ().
	"""
	for s in net.containerServer.values ():
		if s.container:
			reset_docker (s.ip)


def reset_docker (server_ip: str):
	send_data ('GET', '/docker/reset', server_ip, agent_port)


def send_device_nfs (net: Net):
	"""
	send the nfs settings to devices.
	this request can be received by worker/agent.py, route_device_nfs ().
	"""
	tasks = [executor.submit (send_device_nfs_helper, d, net.ip)
	         for d in net.device.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def send_device_nfs_helper (device: Device, ip: str):
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
	send the tc settings to devices.
	this request can be received by worker/agent.py, route_device_tc ().
	"""
	global tc_number
	for d in net.device.values ():
		data = {
			'NET_NODE_NIC': d.nic,
			'NET_NODE_TC': d.tc,
			'NET_NODE_TC_IP': d.tcIP,
			'NET_NODE_TC_PORT': d.tcPort
		}
		print ('device_tc_update: send to ' + d.name)
		res = send_data ('POST', '/device/tc', d.ip, agent_port,
			data={'data': json.dumps (data)})
		if res == '1':
			print ('device ' + d.name + ' tc succeed')
			tc_lock.acquire ()
			tc_number += len (d.tc)
			if tc_number == net.tcLinkNumber:
				print ('tc finish')
			tc_lock.release ()
		else:
			print ('device ' + d.name + ' tc failed, err:')
			print (res)


def send_device_env (net: Net):
	"""
	send the env to devices.
	this request can be received by worker/agent.py, route_device_env ().
	"""
	for d in net.device.values ():
		data = {
			'NET_CTL_ADDRESS': net.address,
			'NET_AGENT_IP': d.ip,
			'NET_NODE_NAME': d.name,
			'NET_NODE_ENV': d.env,
		}
		print ('send_device_env: send to ' + d.name)
		send_data ('POST', '/device/env', d.ip, agent_port,
			data={'data': json.dumps (data)})


def sent_device_req (net: Net, path: str):
	"""
	send the dml_req.txt to devices.
	this request can be received by worker/agent.py, route_device_req ().
	"""
	tasks = [executor.submit (sent_device_req_helper, d, path)
	         for d in net.device.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def sent_device_req_helper (device: Device, path: str):
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
	send a start message to devices.
	this request can be received by worker/agent.py, route_device_start ().
	"""
	tasks = [executor.submit (deploy_device, d) for d in net.device.values ()]
	wait (tasks, return_when=ALL_COMPLETED)


def deploy_device (device: Device):
	data = {'dir': device.workingDir, 'cmd': device.cmd}
	send_data ('POST', '/device/start', device.ip, agent_port,
		data={'data': json.dumps (data)})


def device_controller_listener (app, net: Net):
	"""
	this function can listen command from user.
	it can controller devices.
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
	send a stop message to devices.
	kill the process started by above deploy_device ().
	this request can be received by worker/agent.py, route_device_stop ().
	"""
	for d in net.device.values ():
		stop_device (d.ip)


def stop_device (device_ip: str):
	send_data ('GET', '/device/stop', device_ip, agent_port)


def clear_all_device_tc (net: Net):
	"""
	send a clear tc message to devices.
	clear all tc settings.
	this request can be received by worker/agent.py, route_device_clear_tc ().
	"""
	for d in net.device.values ():
		clear_device_tc (d.ip)


def clear_device_tc (device_ip: str):
	send_data ('GET', '/device/clear/tc', device_ip, agent_port)


def clear_all_device_nfs (net: Net):
	"""
	send a clear nfs message to devices.
	unmount all nfs.
	this request can be received by worker/agent.py, route_device_clear_nfs ().
	"""
	for d in net.device.values ():
		clear_device_nfs (d.ip)


def clear_device_nfs (device_ip: str):
	send_data ('GET', '/device/clear/nfs', device_ip, agent_port)


def reset_all_device (net: Net):
	"""
	send a reset message to devices.
	kill the process started by above deploy_device ().
	clear all tc settings.
	unmount all nfs.
	this request can be received by worker/agent.py, route_device_reset ().
	"""
	for d in net.device.values ():
		reset_device (d.ip)


def reset_device (device_ip: str):
	send_data ('GET', '/device/reset', device_ip, agent_port)


def update_tc_listener (app, net: Net):
	@app.route ('/update/tc', methods=['GET'])
	def route_update_tc ():
		"""
		this function can listen command from user.
		it can update the tc settings of containers and/or devices.
		"""
		path = request.args.get ('path')
		if path [0] != '/':
			path = os.path.join (dirname, path)
		bw_json = read_json (path)
		order = bw_json ['order']
		bw = bw_json ['bw']
		nodes = []
		servers = {}  # server object to container objects in this server.
		for name in bw:
			n = net.name_to_node (name)
			nodes.append (n)
			n.tc.clear ()
			n.tcIP.clear ()
			n.tcPort.clear ()
		net.load_bw (order, bw)
		for node in nodes:
			if node.name in net.device:
				update_device_tc (node)
			else:
				server = net.container [node.name]
				servers.setdefault (server, []).append (node)
		update_docker_tc (servers)
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
	if res == '1':
		print ('device ' + device.name + ' update tc succeed')
	else:
		print ('device ' + device.name + ' update tc failed, err:')
		print (res)


def update_docker_tc (servers):
	for server in servers:
		data = {}
		for c in servers [server]:
			data [c.name] = {
				'NET_NODE_NIC': c.nic,
				'NET_NODE_TC': c.tc,
				'NET_NODE_TC_IP': c.tcIP,
				'NET_NODE_TC_PORT': c.tcPort
			}
		print ('update_docker_tc: send to ' + server.name)
		res = send_data ('POST', '/docker/tc/update', server.ip, agent_port,
			data={'data': json.dumps (data)})
		ret = json.loads (res)
		for name in ret:
			if ret [name] ['number'] == '-1':
				print ('container ' + server.name + ': ' + name + ' update tc failed, err:')
				print (ret [name] ['msg'])
			else:
				print ('container ' + server.name + ': ' + name + ' update tc succeed')
