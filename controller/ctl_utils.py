import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import matplotlib.pyplot as plt
import requests
from flask import request

executor = ThreadPoolExecutor (1)
ready_number = 0
ready_lock = threading.Lock ()
log_name = []
log_lock = threading.Lock ()


def read_json (filename):
	with open (filename, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


def tc_listener (app, net, on_ready=None, *args, **kwargs):
	"""
	this function can listen message from net/worker/worker_tc_init.py, container_load_tc ().
	it will return TC settings to container, and listen for response.
	after all containers have applied the TC settings, it will call the on_ready function.
	"""
	if net.tcLinkNumber == 0:
		return

	@app.route ('/tc', methods=['POST'])
	def route_tc ():
		name = request.form ['name']
		server_name = request.form ['server_name']
		if server_name != 'none':
			n = net.containerServer [server_name].container [name]
		else:
			n = net.device [name]
		data = {'nic': n.nic, 'tc': n.tc, 'tc_ip': n.tcIP}
		return json.dumps (data)

	@app.route ('/tcReady', methods=['GET'])
	def route_tc_ready ():
		number = request.args.get ('number', type=int)
		global ready_number
		ready_lock.acquire ()
		ready_number += number
		if ready_number == net.tcLinkNumber and on_ready:
			on_ready (*args, **kwargs)
		ready_lock.release ()
		return ''


def send_device_conf (net):
	"""
	send TC settings and envs to device.
	this request can be received by net/worker/worker_tc_init.py, device_conf_listener ().
	"""
	for d in net.device.values ():
		data = {
			'NET_CTL_ADDRESS': net.address,
			'NET_DEVICE_NAME': d.name,
			'NET_DEVICE_NIC': d.nic,
			'NET_DEVICE_ENV': json.dumps (d.env),
			'NET_DEVICE_TC': json.dumps (d.tc),
			'NET_DEVICE_TC_IP': json.dumps (d.tcIP),
			'NET_DEVICE_TC_PORT': json.dumps (d.tcPort)
		}
		try:
			requests.post ('http://' + d.ip + ':4444/tcConf', data=data)
		except requests.exceptions.ConnectionError:
			pass


def print_listener (app):
	"""
	this function can listen message from net/worker/worker_utils.py, send_print ().
	print whatever from worker.
	"""

	@app.route ('/print', methods=['POST'])
	def route_print ():
		print (request.form ['msg'])
		return ''


def parse_log (log_file_path, name, initial_acc):
	"""
	parse log files into pictures.
	the log files format comes from net/worker/worker_utils.py, log_acc () and log_loss ().
	Aggregate: accuracy=0.8999999761581421, round=1, layer=2,
	Train: loss=0.2740592360496521, round=1,
	we left a comma at the end for easy positioning and extending.
	"""
	acc_str = 'accuracy='
	layer_str = 'layer='
	loss_str = 'loss='
	acc_map = {}
	loss_list = []
	path = os.path.join (log_file_path, name + '.log')
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
		upper = (loss_list [0] / 10 + max (loss_list [0] / 100, 1)) * 10
		plt.plot (loss_list, 'go')
		plt.plot (loss_list, 'r')
		plt.xlabel ('round')
		plt.ylabel ('loss')
		plt.ylim (0, int (upper))
		plt.title ('Loss')
		path = os.path.join (log_file_path, 'png/', name + '-loss.png')
		plt.savefig (path)
		plt.cla ()


def log_listener (app, log_file_path, total_number, initial_acc=0.0):
	"""
	this function can listen log files from net/worker/worker_utils.py, send_log ().
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
		filename = file.filename
		file.save (os.path.join (log_file_path, filename))
		log_lock.acquire ()
		log_name.append (filename)
		if len (log_name) == total_number:
			print ('log files collection completed, saved on ' + log_file_path)
			path = os.path.join (log_file_path, 'png/')
			if not os.path.exists (path):
				os.mkdir (path)
			for name in log_name:
				parse_log (log_file_path, name, initial_acc)
			print ('log files parsing completed, saved on ' + log_file_path + '/png')
			log_name.clear ()
		log_lock.release ()
		return ''
