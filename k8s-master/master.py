import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from flask import Flask, request


def host_to_index (_host):
	if _host [0] == 'n':
		return int (_host [1:]) + _device_number - 1
	return _device_number - int (_host [1:])


def read_json (filename):
	file_path = os.path.abspath (os.path.join (dirname, filename))
	with open (file_path, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


# 0：EL，1：FL，2：GL
_type = 0  # The only configurable parameter

app = Flask (__name__)
executor = ThreadPoolExecutor (1)
dirname = os.path.dirname (__file__)

env_addr_json = read_json ('tools/env_addr.txt')
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
receive_number = 0
receive_lock = threading.Lock ()


@app.route ('/hi', methods=['GET'])
def route_hi ():
	return 'Master in 9000\r\n'


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
		file_path = os.path.abspath (os.path.join (dirname, 'perf.txt'))
		with open (file_path, 'w') as f:
			f.write (json.dumps (perf))
		print ('write in perf.txt')
	receive_lock.release ()
	# TODO 生成env，然后调用on_route_conf
	return ''


@app.route ('/conf', methods=['GET'])
def route_conf ():
	executor.submit (on_route_conf)
	return ''


def on_route_conf ():
	global log_file_path
	log_file_path = os.path.abspath (
		os.path.join (dirname, 'log/', time.strftime ('%Y-%m-%d-%H-%M-%S', time.localtime (time.time ()))))
	os.makedirs (log_file_path)

	for host in _device_ip:
		file_path = os.path.abspath (os.path.join (dirname, 'env/', host + '.env'))
		with open (file_path, 'r') as f:
			try:
				requests.post ('http://' + _device_ip [host] + ':8888/env', files={'env': f})
			except requests.exceptions.ConnectionError:
				pass
			print ('sent env to ' + host)

	for addr in _container_addr:
		file_path = os.path.abspath (os.path.join (dirname, 'env/', 'n' + str (int (addr [-5:]) - 30000) + '.env'))
		with open (file_path, 'r') as f:
			try:
				requests.post ('http://' + addr + '/env', files={'env': f})
			except requests.exceptions.ConnectionError:
				pass
			print ('sent env to n' + str (int (addr [-5:]) - 30000))


@app.route ('/ready', methods=['GET'])
def route_ready ():
	executor.submit (on_route_ready)
	return ''


def on_route_ready ():
	global receive_number
	receive_lock.acquire ()
	receive_number += 1
	if receive_number == _total_number:
		receive_number = 0
		env_tree_json = read_json ('tools/env_tree.txt')
		top_node_id = env_tree_json ['host_list'] [0] ['id']
		if top_node_id > 0:
			top_node_addr = _container_addr [top_node_id - 1]
		else:
			top_node_addr = _device_ip ['r' + str (-top_node_id)] + ':8888'
		print (requests.get ('http://' + top_node_addr + '/start?type=' + _type))
	receive_lock.release ()


@app.route ('/finish', methods=['GET'])
def route_finish ():
	print ('>>>>>training ended<<<<<')
	executor.submit (on_route_finish)
	return ''


def on_route_finish ():
	for ip in _device_ip.values ():
		requests.get ('http://' + ip + ':8888/log')
	for addr in _container_addr:
		requests.get ('http://' + addr + '/log')


@app.route ('/print', methods=['GET'])
def route_print ():
	print (request.args.get ('msg'))
	return ''


@app.route ('/log', methods=['POST'])
def route_log ():
	executor.submit (on_route_log)
	return ''


def on_route_log ():
	global receive_number
	receive_lock.acquire ()
	file = request.files.get ('log')
	file_path = os.path.join (log_file_path, file.filename)
	file.save (file_path)
	receive_number += 1
	if receive_number == _total_number:
		receive_number = 0
		# TODO 解析.log文件变成图片什么的
		print ('>>>>>all .log got<<<<<')
	receive_lock.release ()


app.run (host='0.0.0.0', port='9000', threaded=True)
