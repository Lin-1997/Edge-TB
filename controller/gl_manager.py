import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import matplotlib.pyplot as plt
from flask import request

import ctl_utils

# this port number should be the same as the one defined in controller/dml_app/gl_peer.py.
dml_port = 4444

executor = ThreadPoolExecutor ()
dirname = os.path.abspath (os.path.dirname (__file__))

node_ip_json = {}
pn_to_ip = {}  # physical node's name to physical node's ip.
en_to_ip = {}  # emulated node's name to emulated node's ip.
en_to_port = {}  # emulated node's name to emulated node's mapped host port.

log_file_path = ''
node_number = 0
log_name = []
log_lock = threading.Lock ()


def manager (app, net):
	global node_number

	with open (os.path.join (dirname, 'node_ip.json'), 'r') as f_node_ip:
		node_ip_json.update (json.loads (f_node_ip.read ()))

	emulator_to_ip = node_ip_json ['emulator']  # emulator's name to emulator's ip.
	emulator_to_node = node_ip_json ['emulated_node']  # emulator's name to node's name inside this emulator.
	pn_to_ip.update (node_ip_json ['physical_node'])
	node_number = len (pn_to_ip)
	for emulator_name in emulator_to_node:
		node_number += len (emulator_to_node [emulator_name])
		for node_name in emulator_to_node [emulator_name]:
			# we assume that you followed the rules stated in controller/ctl_run_example.py.
			# emulated nodes map port 4444 to host port 8000+x.
			en_to_ip [node_name] = emulator_to_ip [emulator_name]
			en_to_port [node_name] = 8000 + int (node_name [1:])

	# send the conf file to the corresponding node.
	@app.route ('/conf', methods=['GET'])
	def route_conf ():
		conf_type = request.args.get ('type', type=int)
		if conf_type == 1:
			executor.submit (on_route_conf, 'dataset')
			return ''
		elif conf_type == 2:
			executor.submit (on_route_conf, 'structure')
			return ''
		else:
			return 'error type'

	def on_route_conf (conf_type):
		for name in pn_to_ip:
			file_path = os.path.join (dirname, 'dml_file/conf', name + '_' + conf_type + '.conf')
			with open (file_path, 'r') as f:
				print ('sent ' + conf_type + ' conf to ' + name)
				ctl_utils.send_data ('POST', '/conf/' + conf_type,
					pn_to_ip [name], dml_port, files={'conf': f})
		for name in en_to_ip:
			file_path = os.path.join (dirname, 'dml_file/conf', name + '_' + conf_type + '.conf')
			with open (file_path, 'r') as f:
				print ('sent ' + conf_type + ' conf to ' + name)
				ctl_utils.send_data ('POST', '/conf/' + conf_type,
					en_to_ip [name], en_to_port [name], files={'conf': f})

	@app.route ('/start', methods=['GET'])
	def route_start ():
		for name in pn_to_ip:
			ctl_utils.send_data ('GET', '/start', pn_to_ip [name], dml_port)
		for name in en_to_ip:
			ctl_utils.send_data ('GET', '/start', en_to_ip [name], en_to_port [name])

		global log_file_path
		# create a folder to save the log files of nodes when finish.
		if log_file_path == '':
			log_file_path = os.path.join (dirname, 'dml_file/log',
				time.strftime ('%Y-%m-%d-%H-%M-%S', time.localtime (time.time ())))
		print ('start training')
		return ''

	# ask for log files.
	@app.route ('/finish', methods=['GET'])
	def route_finish ():
		# create a folder to save the log files of nodes.
		os.makedirs (log_file_path)
		print ('training completed')
		for name in pn_to_ip:
			ctl_utils.send_data ('GET', '/log', pn_to_ip [name], dml_port)
		for name in en_to_ip:
			ctl_utils.send_data ('GET', '/log', en_to_ip [name], en_to_port [name])
		return ''

	@app.route ('/log', methods=['POST'])
	def route_log ():
		"""
		this function can listen log files from worker/worker_utils.py, send_log ().
		log files will be saved on ${log_file_path}.
		when total_number files are received, it will parse these files into pictures
		and save them on ${log_file_path}/png.
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
		print ('try to stop all physical nodes')
		ctl_utils.stop_all_device (net)
		print ('try to clear all emulated nodes')
		ctl_utils.stop_all_docker (net)

	def parse_log (path: str, filename: str):
		"""
		parse log files into pictures.
		the log files format comes from worker/worker_utils.py, log_acc () and log_loss ().
		Aggregate: accuracy=0.8999999761581421, round=1,
		Train: loss=0.2740592360496521, round=1,
		we left a comma at the end for easy positioning and extending.
		"""
		acc_str = 'accuracy='
		loss_str = 'loss='
		acc_list = []
		loss_list = []
		with open (os.path.join (path, filename), 'r') as f:
			for line in f:
				if line.find ('Aggregate') != -1:
					acc_start_i = line.find (acc_str) + len (acc_str)
					acc_end_i = line.find (',', acc_start_i)
					acc = float (line [acc_start_i:acc_end_i])
					acc_list.append (acc)
				elif line.find ('Train') != -1:
					loss_start_i = line.find (loss_str) + len (loss_str)
					loss_end_i = line.find (',', loss_start_i)
					loss = float (line [loss_start_i:loss_end_i])
					loss_list.append (loss)
		name = filename [:filename.find ('.log')]
		if acc_list:
			plt.plot (acc_list, 'go')
			plt.plot (acc_list, 'r')
			plt.xlabel ('round')
			plt.ylabel ('accuracy')
			plt.ylim (0, 1)
			plt.title ('Accuracy')
			plt.savefig (os.path.join (path, 'png/', name + '-acc.png'))
			plt.cla ()
		if loss_list:
			upper = loss_list [0] * 1.2
			plt.plot (loss_list, 'go')
			plt.plot (loss_list, 'r')
			plt.xlabel ('round')
			plt.ylabel ('loss')
			plt.ylim (0, upper)
			plt.title ('Loss')
			plt.savefig (os.path.join (path, 'png/', name + '-loss.png'))
			plt.cla ()
