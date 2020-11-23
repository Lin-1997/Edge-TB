"""
copy this file into your project, if it is useful :-)
"""
import json
import logging
import os

import requests
from apscheduler.schedulers.background import BackgroundScheduler


def read_json (filename):
	with open (filename, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


def device_read_env (path):
	"""
	used by device.
	read device_env.txt saved by worker_tc_init.py, device_conf_listener (),
	and save envs to the system environment.
	:param path: a directory without file name.
	"""
	if os.path.exists ('/.dockerenv'):  # is docker container.
		return
	filename = os.path.abspath (os.path.join (path, 'device_env.txt'))
	env = read_json (filename)
	for k in env:
		os.environ [k] = env [k]


def async_heartbeat (ctl_addr, node_name, interval=30):
	"""
	send a heartbeat to controller periodically.
	this request can be received by controller/ctl_utils.py, heartbeat_listener ().
	"""
	if not ctl_addr:
		return
	path = 'http://' + ctl_addr + '/heartbeat?name=' + node_name \
	       + '&interval=' + str (interval)
	logging.getLogger ('apscheduler').setLevel (logging.ERROR)
	s = BackgroundScheduler ()
	s.add_job (lambda: requests.get (path), 'interval', seconds=interval)
	s.start ()


def send_print (ctl_addr, message):
	"""
	send a message to controller for printing.
	this request can be received by controller/ctl_utils.py, print_listener ().
	"""
	print (message)
	if not ctl_addr:
		return
	try:
		requests.post ('http://' + ctl_addr + '/print', data={'msg': message})
	except requests.exceptions.ConnectionError:
		pass


def set_log (name):
	"""
	log file will be saved on here.
	this function should be called before calling the following logging functions.
	"""
	filename = os.path.abspath (os.path.join (os.path.dirname (__file__),
		'log/', name + '.log'))
	logging.basicConfig (level=logging.INFO, filename=filename,
		filemode='w', format='%(message)s')
	return filename


def log (message):
	"""
	record some messages.
	"""
	logging.info (message)  # log in file.
	print (message)  # print to STDOUT.


def log_loss (loss, _round):
	"""
	we left a comma at the end for easy positioning and extending.
	this message can be parse by controller/ctl_utils.py, parse_log ().
	"""
	msg = 'Train: loss={}, round={},'.format (loss, _round)
	logging.info (msg)
	return msg


def log_acc (acc, _round, layer=-1):
	"""
	we left a comma at the end for easy positioning and extending.
	this message can be parsed by controller/ctl_utils.py, parse_log ().
	"""
	msg = 'Aggregate: accuracy={}, round={}, layer={},'.format (acc, _round, layer)
	logging.info (msg)
	return msg


def send_log (ctl_addr, filename, hostname):
	"""
	send log file to controller.
	this request can be received by controller/ctl_utils.py, log_listener ().
	"""
	if not ctl_addr:
		return
	with open (filename, 'r') as f:
		try:
			requests.post ('http://' + ctl_addr + '/log?host=' + hostname, files={'log': f})
		except requests.exceptions.ConnectionError:
			pass
