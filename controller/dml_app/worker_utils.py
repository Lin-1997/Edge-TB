import logging
from typing import Dict, IO

import requests


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
	@return: response.text.
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


def heartbeat (agent_address: str, node_name: str):
	"""
	send a heartbeat to the agent.
	this request can be received by worker/agent.py, route_heartbeat ().
	"""
	if agent_address:
		path = '/heartbeat?name=' + node_name
		send_data ('GET', path, agent_address)


def send_print (ctl_address: str, message: str):
	"""
	send a message to controller for printing.
	this request can be received by controller/ctl_utils.py, print_listener ().
	"""
	if ctl_address:
		send_data ('POST', '/print', ctl_address, data={'msg': message})


def set_log (filename: str):
	"""
	log file will be saved on ${filename}.
	this function should be called before calling the following logging functions.
	"""
	logging.basicConfig (level=logging.INFO, filename=filename,
		filemode='w', format='%(message)s')


def log (message: str):
	"""
	record some messages.
	"""
	logging.info (message)  # log in file.
	print (message)  # print to STDOUT.


def send_log (ctl_address: str, filename: str, name: str):
	"""
	send log file to controller.
	this request can be received by controller/ctl_utils.py, log_listener ().
	"""
	if ctl_address:
		with open (filename, 'r') as f:
			path = '/log?name=' + name
			send_data ('POST', path, ctl_address, files={'log': f})
