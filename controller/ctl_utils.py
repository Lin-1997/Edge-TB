import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import matplotlib.pyplot as plt
import requests
from flask import request

executor = ThreadPoolExecutor (1)
heartbeat_time = {}
heartbeat_interval = {}
ready_number = 0
ready_lock = threading.Lock ()
log_name = []
log_lock = threading.Lock ()


def read_json (filename):
	with open (filename, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


def heartbeat_listener (app):
	"""
	this function can listen heartbeat from worker/worker_utils.py, async_heartbeat ().
	it will store the received time of nodes heartbeat, and the normal interval time.
	you can send a GET requests to this /all_heartbeat to get how much time
	has passed since nodes last sent a heartbeat, and to /abnormal_heartbeat
	to get the likely abnormal nodes.
	"""

	@app.route ('/heartbeat', methods=['GET'])
	def route_heartbeat ():
		name = request.args.get ('name')
		interval = request.args.get ('interval', type=float, default=30.0)
		_time = time.time ()
		heartbeat_time [name] = _time
		heartbeat_interval [name] = interval
		return ''

	@app.route ('/all_heartbeat', methods=['GET'])
	def route_all_heartbeat ():
		s = 'the last heartbeat of nodes are:\n'
		now = time.time ()
		for name in heartbeat_time:
			_time = now - heartbeat_time [name]
			s = s + name + ' was ' + str (_time) + ' seconds ago. ' \
			    + 'the normal interval should be ' + str (heartbeat_interval [name]) + '.\n'
		return s

	@app.route ('/abnormal_heartbeat', methods=['GET'])
	def route_abnormal_heartbeat ():
		s = 'the last heartbeat of likely abnormal nodes are:\n'
		now = time.time ()
		for name in heartbeat_time:
			_time = now - heartbeat_time [name]
			if _time > heartbeat_interval [name] * 1.1:
				s = s + name + ' was ' + str (_time) + ' seconds ago. ' \
				    + 'the normal interval should be ' + str (heartbeat_interval [name]) + '.\n'
		return s


def tc_listener (app, net):
	"""
	this function can listen message from worker/worker_tc_init.py, container_load_tc ().
	it will return TC settings to container, and listen for response.
	"""

	@app.route ('/tc', methods=['GET'])
	def route_tc ():
		name = request.args.get ('name')
		n = net.name_to_node (name)
		data = {'nic': n.nic, 'tc': n.tc, 'tc_ip': n.tcIP}
		return json.dumps (data)

	@app.route ('/tcReady', methods=['GET'])
	def route_tc_ready ():
		number = request.args.get ('number', type=int)
		global ready_number
		ready_lock.acquire ()
		ready_number += number
		if ready_number == net.tcLinkNumber:
			print ('tc ready')
		ready_lock.release ()
		return ''


def send_device_conf (net):
	"""
	send TC settings and envs to device.
	this request can be received by worker/worker_tc_init.py, device_conf_listener ().
	"""
	global ready_number
	for d in net.device.values ():
		data = {
			'NET_CTL_ADDRESS': net.address,
			'NET_NODE_NAME': d.name,
			'NET_NODE_NIC': d.nic,
			'NET_NODE_ENV': json.dumps (d.env),
			'NET_NODE_TC': json.dumps (d.tc),
			'NET_NODE_TC_IP': json.dumps (d.tcIP),
			'NET_NODE_TC_PORT': json.dumps (d.tcPort)
		}
		res = requests.post ('http://' + d.ip + ':8888/tcConf', data=data)
		ready_lock.acquire ()
		ready_number += int (res.text)
		print ('device tc ready number = ' + res.text)
		if ready_number == net.tcLinkNumber:
			print ('tc ready')
		ready_lock.release ()
		try:
			requests.get ('http://' + d.ip + ':8888/tcFinish')
		except requests.exceptions.ConnectionError:
			pass


def print_listener (app):
	"""
	this function can listen message from worker/worker_utils.py, send_print ().
	print whatever from worker.
	"""

	@app.route ('/print', methods=['POST'])
	def route_print ():
		print (request.form ['msg'])
		return ''


def parse_log (log_file_path, filename, initial_acc):
	"""
	parse log files into pictures.
	the log files format comes from worker/worker_utils.py, log_acc () and log_loss ().
	Aggregate: accuracy=0.8999999761581421, round=1, layer=2,
	Train: loss=0.2740592360496521, round=1,
	we left a comma at the end for easy positioning and extending.
	"""
	acc_str = 'accuracy='
	layer_str = 'layer='
	loss_str = 'loss='
	acc_map = {}
	loss_list = []
	path = os.path.join (log_file_path, filename)
	with open (path, 'r') as f:
		for line in f:
			if line.find ('Aggregate') != -1:
				acc_start_i = line.find (acc_str) + len (acc_str)
				acc_end_i = line.find (',', acc_start_i)
				acc = float (line [acc_start_i:acc_end_i])
				layer_start_i = line.find (layer_str) + len (layer_str)
				layer_end_i = line.find (',', layer_start_i)
				layer = int (line [layer_start_i:layer_end_i])
				acc_map.setdefault (layer, [initial_acc]).append (acc)
			elif line.find ('Train') != -1:
				loss_start_i = line.find (loss_str) + len (loss_str)
				loss_end_i = line.find (',', loss_start_i)
				loss = float (line [loss_start_i:loss_end_i])
				loss_list.append (loss)
	name = filename [:filename.find ('.log')]
	for layer in acc_map:
		plt.plot (acc_map [layer], 'go')
		plt.plot (acc_map [layer], 'r')
		plt.xlabel ('round')
		plt.ylabel ('accuracy')
		plt.ylim (0, 1)
		plt.title ('Accuracy')
		if layer != -1:
			path = os.path.join (log_file_path, 'png/', name + '-L' + str (layer) + '-acc.png')
		else:
			path = os.path.join (log_file_path, 'png/', name + '-acc.png')
		plt.savefig (path)
		plt.cla ()
	if len (loss_list) != 0:
		upper = loss_list [0] * 1.2
		plt.plot (loss_list, 'go')
		plt.plot (loss_list, 'r')
		plt.xlabel ('round')
		plt.ylabel ('loss')
		plt.ylim (0, upper)
		plt.title ('Loss')
		path = os.path.join (log_file_path, 'png/', name + '-loss.png')
		plt.savefig (path)
		plt.cla ()


def log_listener (app, log_file_path, total_number, initial_acc=0.0):
	"""
	this function can listen log files from worker/worker_utils.py, send_log ().
	log files will be saved on log_file_path.
	when total_number files are received, it will parse these files into pictures
	and save them on log_file_path/png.
	if a log file contains accuracy, it will start from initial_acc.
	"""

	@app.route ('/log', methods=['POST'])
	def route_log ():
		host = request.args.get ('host')
		print ('get ' + host + '\'s log')
		file = request.files.get ('log')
		file.save (os.path.join (log_file_path, file.filename))
		log_lock.acquire ()
		log_name.append (file.filename)
		if len (log_name) == total_number:
			print ('log files collection completed, saved on ' + log_file_path)
			path = os.path.join (log_file_path, 'png/')
			if not os.path.exists (path):
				os.mkdir (path)
			for filename in log_name:
				parse_log (log_file_path, filename, initial_acc)
			print ('log files parsing completed, saved on ' + log_file_path + '/png')
			log_name.clear ()
		log_lock.release ()
		return ''
