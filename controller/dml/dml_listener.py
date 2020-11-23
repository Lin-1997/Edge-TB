import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from flask import request

import ctl_utils

# the only configurable parameter.
_type = 0  # 0: EL, 1: FL.

executor = ThreadPoolExecutor (1)
dirname = os.path.abspath (os.path.dirname (__file__))

env_node_ip_json = {}
_server = {}
_container = {}
_device = {}
_container_addr = {}
_total_number = 0
perf = {}
log_file_path = ''
initial_acc = 0.0
receive_number = 0
receive_lock = threading.Lock ()


def listener (app):
	global _total_number
	env_node_ip_json.update (ctl_utils.read_json (os.path.join (dirname, '../node_ip.txt')))
	_server.update (env_node_ip_json ['server'])
	_container.update (env_node_ip_json ['container'])
	_device.update (env_node_ip_json ['device'])
	_total_number = len (_device)
	for s_name in _container:
		_total_number += len (_container [s_name])
		for c_name in _container [s_name]:
			_container_addr [c_name] = _server [s_name] + ':' + str (30000 + int (c_name [1:]))

	@app.route ('/hi', methods=['GET'])
	def route_hi ():
		return 'this is net_ctl\n'

	@app.route ('/perf', methods=['GET'])
	def route_perf ():
		global receive_number
		node = request.args.get ('node')
		total_time = request.args.get ('time', type=float)
		print (node + ' use ' + str (total_time))
		perf [node] = total_time
		receive_lock.acquire ()
		receive_number += 1
		if receive_number == _total_number:
			receive_number = 0
			perf ['size'] = request.args.get ('size', type=float)
			file_path = os.path.join (dirname, 'perf.txt')
			with open (file_path, 'w') as f:
				f.write (json.dumps (perf))
			print ('performance collection completed, saved on ' + file_path)
		receive_lock.release ()
		# TODO 生成env，然后调用on_route_conf
		return ''

	@app.route ('/conf', methods=['GET'])
	def route_conf ():
		executor.submit (on_route_conf)
		return ''

	def on_route_conf ():
		global log_file_path, initial_acc
		log_file_path = os.path.join (dirname, 'log/',
			time.strftime ('%Y-%m-%d-%H-%M-%S', time.localtime (time.time ())))

		for node in _device:
			file_path = os.path.join (dirname, 'env/', node + '.env')
			with open (file_path, 'r') as f:
				requests.post ('http://' + _device [node] + ':8888/env', files={'env': f})
				print ('sent env to ' + node)

		for node in _container_addr:
			file_path = os.path.join (dirname, 'env/', node + '.env')
			with open (file_path, 'r') as f:
				requests.post ('http://' + _container_addr [node] + '/env', files={'env': f})
				print ('sent env to ' + node)

		print ('start training')
		env_tree_json = ctl_utils.read_json (os.path.join (dirname, 'env_tree.txt'))
		top_node_name = env_tree_json ['node_list'] [0] ['name']
		if top_node_name in _device:
			top_node_addr = _device [top_node_name] + ':8888'
		else:
			top_node_addr = _container_addr [top_node_name]
		res = requests.get ('http://' + top_node_addr + '/start?type=' + str (_type))
		initial_acc = float (res.text)
		print ('initial_acc = ' + str (initial_acc))

	@app.route ('/finish', methods=['GET'])
	def route_finish ():
		os.makedirs (log_file_path)
		ctl_utils.log_listener (app, log_file_path, _total_number, initial_acc)
		print ('training completed')
		for _ip in _device.values ():
			requests.get ('http://' + _ip + ':8888/log')
		for addr in _container_addr.values ():
			requests.get ('http://' + addr + '/log')
		return ''
