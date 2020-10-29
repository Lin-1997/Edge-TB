"""
copy this file into your project, if it is useful :-)
"""
import json
import os
import logging

import requests

dirname = os.path.abspath (os.path.dirname (__file__))
ctl_addr = os.getenv ('NET_CTL_ADDRESS')


def read_json (filename):
	with open (filename, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


def send_print (message: str):
	"""
	send a message to controller for printing.
	this request can be received by net/controller/ctl_utils.py, print_listener ().
	"""
	try:
		requests.post ('http://' + ctl_addr + '/print', data={'msg': message})
	except requests.exceptions.ConnectionError:
		pass


def set_log (name: str):
	"""
	log file will be saved on here.
	"""
	filename = os.path.join (dirname, 'log/', name + '.log')
	logging.basicConfig (level=logging.INFO, filename=filename,
		filemode='w', format='%(message)s')
	return filename


def log (message: str):
	"""
	record some messages.
	"""
	logging.info (message)


def log_loss (loss: float, _round: int):
	"""
	we left a comma at the end for easy positioning and extending.
	this message can be parse by net/controller/ctl_utils.py, parse_log ().
	"""
	msg = 'Train: loss={}, round={},'.format (loss, _round)
	logging.info (msg)
	return msg


def log_acc (acc: float, _round: int, layer: int = -1):
	"""
	we left a comma at the end for easy positioning and extending.
	this message can be parsed by net/controller/ctl_utils.py, parse_log ().
	"""
	msg = 'Aggregate: accuracy={}, round={}, layer={},'.format (acc, _round, layer)
	logging.info (msg)
	return msg


def send_log (filename: str, hostname: str):
	"""
	send log file to controller.
	this request can be received by net/controller/ctl_utils.py, log_listener ().
	"""
	with open (filename, 'r') as f:
		try:
			requests.post ('http://' + ctl_addr + '/log?host=' + hostname, files={'log': f})
		except requests.exceptions.ConnectionError:
			pass
