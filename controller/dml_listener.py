import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import matplotlib.pyplot as plt
from flask import request

import ctl_utils

# configurable parameter.
_type = 0  # 0: EL, 1: FL.
# this port number should be the same as the one defined in controller/dml_app/EL.py.
dml_port = 4444

executor = ThreadPoolExecutor (1)
dirname = os.path.abspath (os.path.dirname (__file__))

node_ip_json = {}
device_ip = {}  # device's name to device's ip.
c_ip = {}  # container's name to container's ip.
c_port = {}  # container's name to container's mapped host port.

initial_acc: float
log_file_path = ''
node_number = 0
perf = {}
perf_lock = threading.Lock ()
log_name = []
log_lock = threading.Lock ()


def listener (app, net):
	global node_number
	node_ip_json.update (ctl_utils.read_json (os.path.join (dirname, 'node_ip.txt')))
	server = node_ip_json ['server']  # server's name to server's ip.
	container = node_ip_json ['container']  # server's name to containers' name inside this server.
	device_ip.update (node_ip_json ['device'])
	node_number = len (device_ip)
	for s_name in container:
		node_number += len (container [s_name])
		for c_name in container [s_name]:
			# we assume that you followed the rules stated in controller/ctl_run_example.py.
			# containers map port 4444 to host port 8000+x.
			c_ip [c_name] = server [s_name]
			c_port [c_name] = 8000 + int (c_name [1:])

	# collect the time required for 1 epoch training for each trainer in 1 layer.
	# they may help you decide how often trainers upload weights.
	@app.route ('/perf', methods=['GET'])
	def route_perf ():
		node = request.args.get ('node')
		total_time = request.args.get ('time', type=float)
		print (node + ' use ' + str (total_time))
		perf [node] = total_time
		perf_lock.acquire ()
		if len (perf) == node_number:
			perf ['size'] = request.args.get ('size', type=float)
			file_path = os.path.join (dirname, 'dml_tool/perf.txt')
			with open (file_path, 'w') as f:
				f.write (json.dumps (perf))
			print ('performance collection completed, saved on ' + file_path)
		perf_lock.release ()
		# TODO write controller/dml_tool/conf_structure.txt to define the dml structure,
		#  use controller/dml_tool/conf_generator.py to generate conf files,
		#  and call on_route_conf () by sending a HTTP GET to /conf.
		return ''

	# send the conf file to the corresponding node.
	@app.route ('/conf', methods=['GET'])
	def route_conf ():
		start = request.args.get ('start', type=int, default=0)
		executor.submit (on_route_conf, start)
		return ''

	def on_route_conf (start):
		global log_file_path, initial_acc
		for node in device_ip:
			file_path = os.path.join (dirname, 'dml_file/conf', node + '.conf')
			with open (file_path, 'r') as f:
				print ('sent conf to ' + node)
				ctl_utils.send_data ('POST', '/conf', device_ip [node], dml_port, files={'conf': f})
		for node in c_ip:
			file_path = os.path.join (dirname, 'dml_file/conf', node + '.conf')
			with open (file_path, 'r') as f:
				print ('sent conf to ' + node)
				ctl_utils.send_data ('POST', '/conf', c_ip [node], c_port [node], files={'conf': f})

		if start != 1:
			return
		# create a folder to save the log files of nodes when finish.
		if log_file_path == '':
			log_file_path = os.path.join (dirname, 'dml_file/log',
				time.strftime ('%Y-%m-%d-%H-%M-%S', time.localtime (time.time ())))
		conf_structure_json = ctl_utils.read_json (os.path.join (dirname, 'conf_structure.txt'))
		name = conf_structure_json ['node_list'] [0] ['name']
		print ('start training')
		path = '/start?type=' + str (_type)
		if name in device_ip:
			initial_acc = float (ctl_utils.send_data ('GET', path, device_ip [name], dml_port))
		else:
			initial_acc = float (
				ctl_utils.send_data ('GET', path, c_ip [name], c_port [name]))
		print ('initial acc = ' + str (initial_acc))
		return ''

	# when training is complete, ask for log files.
	@app.route ('/finish', methods=['GET'])
	def route_finish ():
		# create a folder to save the log files of nodes.
		os.makedirs (log_file_path)
		print ('training completed')
		for _ip in device_ip.values ():
			ctl_utils.send_data ('GET', '/log', _ip, dml_port)
		for name in c_ip:
			ctl_utils.send_data ('GET', '/log', c_ip [name], c_port [name])
		return ''

	@app.route ('/log', methods=['POST'])
	def route_log ():
		"""
		this function can listen log files from worker/worker_utils.py, send_log ().
		log files will be saved on ${log_file_path}.
		when total_number files are received, it will parse these files into pictures
		and save them on ${log_file_path}/png.
		if a log file contains accuracy, it will start from initial_acc.
		"""
		name = request.args.get ('name')
		print ('get ' + name + '\'s log')
		request.files.get ('log').save (os.path.join (log_file_path, name + '.log'))
		log_lock.acquire ()
		log_name.append (name + '.log')
		if len (log_name) == node_number:
			print ('log files collection completed, saved on ' + log_file_path)
			full_path = os.path.join (log_file_path, 'png/')
			if not os.path.exists (full_path):
				os.mkdir (full_path)
			for filename in log_name:
				parse_log (log_file_path, filename)
			print ('log files parsing completed, saved on ' + log_file_path + '/png')
			log_name.clear ()
			executor.submit (after_log)
		log_lock.release ()
		return ''

	def after_log ():
		time.sleep (5)
		print ('try to stop all devices')
		ctl_utils.stop_all_device (net)
		print ('try to clear all containers')
		ctl_utils.clear_all_docker (net)

	def parse_log (path: str, filename: str):
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
		with open (os.path.join (path, filename), 'r') as f:
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
			if layer == -1:
				plt.savefig (os.path.join (path, 'png/', name + '-acc.png'))
			else:
				plt.savefig (os.path.join (path, 'png/', name + '-L' + str (layer) + '-acc.png'))
			plt.cla ()
		if len (loss_list) != 0:
			upper = loss_list [0] * 1.2
			plt.plot (loss_list, 'go')
			plt.plot (loss_list, 'r')
			plt.xlabel ('round')
			plt.ylabel ('loss')
			plt.ylim (0, upper)
			plt.title ('Loss')
			plt.savefig (os.path.join (path, 'png/', name + '-loss.png'))
			plt.cla ()
