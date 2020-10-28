import json
import os
import subprocess as sp

import requests
from flask import Flask, request


def container_load_tc ():
	"""
	this function can request TC settings from controller.
	this request can be received by net/controller/ctl_utils.py, tc_listener ().
	"""
	ctl_addr = os.getenv ('NET_CTL_ADDRESS')
	c_name = os.getenv ('NET_CONTAINER_NAME')
	s_name = os.getenv ('NET_SERVER_NAME')
	res = requests.post ('http://' + ctl_addr + '/tc', data={'name': c_name, 'server_name': s_name})
	res_json = json.loads (res.text)
	tc = res_json ['tc']
	if len (tc) != 0:
		nic = res_json ['nic']
		tc_ip = res_json ['tc_ip']
		p = sp.Popen ('tc qdisc show dev %s' % nic, stdout=sp.PIPE, shell=True)
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
				# the svc name comes from controller/class_node.py, ContainerServer.save_yml (), Service.metadata.name.
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
				p = sp.Popen (c % nic, stdout=sp.PIPE, shell=True)
				print (p.communicate () [0].decode ())
			print ('if no error printed, then successfully limited the bw with ' + name + ' to ' + bw)
			cmd.clear ()
		try:
			requests.get ('http://' + ctl_addr + '/tcReady?number=' + str (len (tc)))
		except requests.exceptions.ConnectionError:
			pass


def device_conf_listener ():
	"""
	this function can listen message from net/controller/ctl_utils.py, send_device_conf ().
	it will apply TC settings and save envs to the system environment.
	"""
	app = Flask (__name__)

	@app.route ('/tcConf', methods=['POST'])
	def route_tc_conf ():
		data = request.form
		net_ctl_address = data ['NET_CTL_ADDRESS']
		os.putenv ('NET_CTL_ADDRESS', net_ctl_address)
		os.putenv ('NET_DEVICE_NAME', data ['NET_DEVICE_NAME'])
		nic = data ['NET_DEVICE_NIC']
		os.putenv ('NET_DEVICE_NIC', nic)
		env = json.loads (data ['NET_DEVICE_ENV'])
		for k in env:
			os.putenv (k, env [k])

		tc = json.loads (data ['NET_DEVICE_TC'])
		if len (tc) != 0:
			tc_ip = json.loads (data ['NET_DEVICE_TC_IP'])
			tc_port = json.loads (data ['NET_DEVICE_TC_PORT'])
			p = sp.Popen ('sudo tc qdisc show dev %s' % nic, stdout=sp.PIPE, shell=True)
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
					p = sp.Popen (c % nic, stdout=sp.PIPE, shell=True)
					print (p.communicate () [0].decode ())
				print ('if no error printed, then successfully limited the bw with ' + name + ' to ' + bw)
				cmd.clear ()

			try:
				requests.get ('http://' + net_ctl_address + '/tcReady?number=' + str (len (tc)))
			except requests.exceptions.ConnectionError:
				pass

		exit ()

	app.run (host='0.0.0.0', port=4444, threaded=False)


if __name__ == '__main__':
	if os.path.exists ('/.dockerenv'):  # is docker container.
		container_load_tc ()
	else:  # is device.
		device_conf_listener ()
