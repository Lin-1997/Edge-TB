import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from flask import request

import ctl_utils

# the only configurable parameter.
_type = 0  # 0: EL, 1: FL, 2: GL.

executor = ThreadPoolExecutor (1)
dirname = os.path.abspath (os.path.dirname (__file__))
env_addr_json = ctl_utils.read_json (os.path.join (dirname, 'tools/env_addr.txt'))
_device_number = env_addr_json ['device_number']
_container_number = env_addr_json ['container_number']
_total_number = _device_number + _container_number [-1]
_server_ip = env_addr_json ['server_ip']
_device_ip = env_addr_json ['device_ip']
_container_addr = []
start_i = 0
for ip_i in range (len (_server_ip)):
	end_i = _container_number [ip_i]
	for c_i in range (end_i - start_i):
		_container_addr.append (_server_ip [ip_i] + ':' + str (30001 + c_i + start_i))
	start_i = end_i

perf = {}
log_file_path = ''
log_file_time = ''
initial_acc = 0.0
receive_number = 0
receive_lock = threading.Lock ()


def listener (app):
	@app.route ('/hi', methods=['GET'])
	def route_hi ():
		return 'this is net_ctl\n'

	@app.route ('/perf', methods=['GET'])
	def route_perf ():
		global receive_number
		host = request.args.get ('host')
		total_time = request.args.get ('time', type=float)
		print (host + ' use ' + str (total_time))
		perf [host] = total_time
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
		global log_file_path
		log_file_path = os.path.join (dirname, 'log/',
			time.strftime ('%Y-%m-%d-%H-%M-%S', time.localtime (time.time ())))

		if _device_number > 0:
			for host in _device_ip:
				file_path = os.path.join (dirname, 'env/', host + '.env')
				with open (file_path, 'r') as f:
					try:
						requests.post ('http://' + _device_ip [host] + ':8888/env', files={'env': f})
					except requests.exceptions.ConnectionError:
						pass
					print ('sent env to ' + host)

		for addr in _container_addr:
			file_path = os.path.join (dirname, 'env/', 'n' + str (int (addr [-5:]) - 30000) + '.env')
			with open (file_path, 'r') as f:
				try:
					requests.post ('http://' + addr + '/env', files={'env': f})
				except requests.exceptions.ConnectionError:
					pass
				print ('sent env to n' + str (int (addr [-5:]) - 30000))

	@app.route ('/ready', methods=['GET'])
	def route_ready ():
		host = request.args.get ('host')
		print (host + ' is ready')
		executor.submit (on_route_ready)
		return ''

	def on_route_ready ():
		global receive_number, initial_acc
		receive_lock.acquire ()
		receive_number += 1
		if receive_number == _total_number:
			receive_number = 0
			time.sleep (5)
			print ('all nodes ready')
			env_tree_json = ctl_utils.read_json (os.path.join (dirname, 'tools/env_tree.txt'))
			top_node_id = env_tree_json ['host_list'] [0] ['id']
			if top_node_id > 0:
				top_node_addr = _container_addr [top_node_id - 1]
			else:
				top_node_addr = _device_ip ['r' + str (-top_node_id)] + ':8888'
			res = requests.get ('http://' + top_node_addr + '/start?type=' + str (_type))
			initial_acc = float (res.text)
			print ('initial_acc = ' + str (initial_acc))
		receive_lock.release ()

	@app.route ('/finish', methods=['GET'])
	def route_finish ():
		os.makedirs (log_file_path)
		ctl_utils.log_listener (app, log_file_path, _total_number, initial_acc)
		print ('training completed')
		if _device_number > 0:
			for _ip in _device_ip.values ():
				requests.get ('http://' + _ip + ':8888/log')
		for addr in _container_addr:
			requests.get ('http://' + addr + '/log')
		return ''
