import json
import threading

import requests
from flask import request

ready_number = 0
ready_number_lock = threading.Lock ()


def tc_listener (app, net, on_ready=None, *args, **kwargs):
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
		ready_number_lock.acquire ()
		ready_number += number
		if ready_number == net.tcLinkNumber and on_ready:
			on_ready (*args, **kwargs)
		ready_number_lock.release ()
		return ''


def print_listener (app):
	@app.route ('/print', methods=['POST'])
	def route_print ():
		print (request.form ['msg'])
		return ''


def send_device_conf (net):
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
