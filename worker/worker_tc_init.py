import json
import os
import subprocess as sp
import time

import requests
from flask import Flask, request


def container_load_tc ():
	"""
	this function can request TC settings from controller.
	this request can be received by controller/ctl_utils.py, tc_listener ().
	"""
	ctl_addr = os.getenv ('NET_CTL_ADDRESS')
	node_name = os.getenv ('NET_NODE_NAME')
	res = requests.get ('http://' + ctl_addr + '/tc?name=' + node_name)
	res_json = json.loads (res.text)
	tc = res_json ['tc']
	if len (tc) != 0:
		nic = res_json ['nic']
		tc_ip = res_json ['tc_ip']
		p = sp.Popen ('tc qdisc show dev %s' % nic, stdout=sp.PIPE, stderr=sp.STDOUT, shell=True)
		out = p.communicate () [0].decode ()
		if "priomap" not in out and "noqueue" not in out:
			cmd = ['tc qdisc del dev %s root']
		else:
			cmd = []
		cmd.append ('tc qdisc add dev %s root handle 1: htb default 1')
		cmd.append ('tc class add dev %s parent 1: classid 1:1 htb rate 10gbps ceil 10gbps burst 15k')
		i = 10
		for name in tc.keys ():
			if name in tc_ip:
				# is a device.
				ip = tc_ip [name]
			else:
				# is a container.
				# the svc name comes from controller/class_node.py, ContainerServer.save_k8s_yml (), Service.metadata.name.
				# the format is s-$(container.name).
				# k8s will save it in system env as $(Service.metadata.name)_SERVICE_HOST in uppercase and replace all '-' to '_'.
				# for convenience, we hardcode it, and we do not recommend modifying it.
				svc = ('s-' + name + '_SERVICE_HOST').upper ().replace ('-', '_')
				ip = os.getenv (svc)

			bw = tc [name]
			cmd.append (
				'tc class add dev %s parent 1:1 classid ' + '1:%d htb rate %s ceil %s burst 15k' % (i, bw, bw))
			cmd.append ('tc filter add dev %s protocol ip parent 1: prio 2 u32 match ip dst '
			            + '%s/32 flowid 1:%d' % (ip, i))
			i += 1
			for c in cmd:
				p = sp.Popen (c % nic, stdout=sp.PIPE, stderr=sp.STDOUT, shell=True)
				print (p.communicate () [0].decode ())
			print ('if no error printed, then successfully limited the bw with ' + name + ' to ' + bw)
			cmd.clear ()
		# end for name in tc.keys ()
		requests.get ('http://' + ctl_addr + '/tcReady?number=' + str (len (tc)))


def device_conf_listener ():
	"""
	this function can listen message from controller/ctl_utils.py, send_device_conf ().
	it will apply TC settings and save envs as device_env.txt in json format.
	the txt file can be read by worker/worker_utils.py, device_read_env ().
	"""
	app = Flask (__name__)

	@app.route ('/tcConf', methods=['POST'])
	def route_tc_conf ():
		data = request.form
		env = json.loads (data ['NET_NODE_ENV'])
		env ['NET_CTL_ADDRESS'] = data ['NET_CTL_ADDRESS']
		env ['NET_NODE_NAME'] = data ['NET_NODE_NAME']
		with open ('device_env.txt', 'w') as f:
			json.dump (env, f)

		nic = data ['NET_NODE_NIC']
		tc = json.loads (data ['NET_NODE_TC'])
		if len (tc) != 0:
			tc_ip = json.loads (data ['NET_NODE_TC_IP'])
			tc_port = json.loads (data ['NET_NODE_TC_PORT'])
			p = sp.Popen ('sudo tc qdisc show dev %s' % nic, stdout=sp.PIPE, stderr=sp.STDOUT, shell=True)
			out = p.communicate () [0].decode ()
			if "priomap" not in out and "noqueue" not in out:
				cmd = ['sudo tc qdisc del dev %s root']
			else:
				cmd = []
			cmd.append ('sudo tc qdisc add dev %s root handle 1: htb default 1')
			cmd.append ('sudo tc class add dev %s parent 1: classid 1:1 htb rate 10gbps ceil 10gbps burst 15k')
			i = 10
			for name in tc.keys ():
				ip = tc_ip [name]
				bw = tc [name]
				cmd.append (
					'sudo tc class add dev %s parent 1:1 classid ' + '1:%d htb rate %s ceil %s burst 15k' % (i, bw, bw))
				if name in tc_port:
					# is a container.
					# all nodePorts of this container share the same limit.
					for port in tc_port [name]:
						cmd.append ('sudo tc filter add dev %s protocol ip parent 1: prio 2 u32 match ip dst '
						            + '%s/32 match ip dport %d 0xffff flowid 1:%d' % (ip, port, i))
				else:
					# is a device.
					cmd.append ('sudo tc filter add dev %s protocol ip parent 1: prio 2 u32 match ip dst '
					            + '%s/32 flowid 1:%d' % (ip, i))
				i += 1
				for c in cmd:
					p = sp.Popen (c % nic, stdout=sp.PIPE, stderr=sp.STDOUT, shell=True)
					print (p.communicate () [0].decode ())
				print ('if no error printed, then successfully limited the bw with ' + name + ' to ' + bw)
				cmd.clear ()
		return str (len (tc))

	@app.route ('/tcFinish', methods=['GET'])
	def route_tc_finish ():
		exit ()

	app.run (host='0.0.0.0', port=8888, threaded=False)


if __name__ == '__main__':
	sleep = 5  # the only configurable parameter.
	# avoid that the controller is not running the Flask server.
	# if you start many containers, consider setting a longer time.
	if os.path.exists ('/.dockerenv'):  # is docker container.
		time.sleep (sleep)
		container_load_tc ()
	else:  # is device.
		device_conf_listener ()
