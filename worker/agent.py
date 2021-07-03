import atexit
import json
import os
import socket
import subprocess as sp
import time
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from typing import Dict, List

import requests
from flask import Flask, request

# we do not recommend changing this port number, but if you really want to change it,
# you need to change controller/ctl_utils.py together.
agent_port = 3333
executor = ThreadPoolExecutor ()
app = Flask (__name__)
dirname = os.path.abspath (os.path.dirname (__file__))
hostname = socket.gethostname ()
heartbeat = {}
tc_data = {}
ctl_addr: str
dml_p: sp.Popen


@app.route ('/hi', methods=['GET'])
def route_hi ():
	return 'this is agent ' + hostname + '\n'


@app.route ('/heartbeat', methods=['GET'])
def route_heartbeat ():
	"""
	this function can listen message from worker/worker_utils.py, heartbeat ().
	it will store the time of nodes heartbeat.
	when it receives the heartbeat of a container for the first time,
	it will deploy the container's tc settings.
	"""
	name = request.args.get ('name')
	t_time = time.time ()
	# deploy the container's tc settings.
	if name not in heartbeat and name in tc_data:
		ret = deploy_docker_tc (name)
		if ret:
			ret ['name'] = hostname + ': ' + name
			requests.post ('http://' + ctl_addr + '/docker/tc', data={'data': json.dumps (ret)})
	heartbeat [name] = t_time
	return ''


def deploy_docker_tc (name: str) -> Dict:
	data = tc_data [name]
	tc = data ['NET_NODE_TC']
	nic = data ['NET_NODE_NIC']
	prefix = 'sudo docker exec ' + name + ' '
	clear_tc_helper (prefix, nic)
	if tc:
		tc_ip = data ['NET_NODE_TC_IP']
		tc_port = data ['NET_NODE_TC_PORT']
		cmd = deploy_tc_helper (prefix, nic, tc, tc_ip, tc_port)
		p = sp.Popen (' && '.join (cmd), stdout=sp.PIPE, stderr=sp.STDOUT, shell=True, close_fds=True)
		msg = p.communicate () [0].decode ()
		if msg != '':
			print (name + ' tc failed, err:')
			print (msg)
			return {'number': '-1', 'msg': msg}
		else:
			print (name + ' tc succeed')
			return {'number': str (len (tc))}

	return {}


@app.route ('/heartbeat/all', methods=['GET'])
def route_heartbeat_all ():
	"""
	you can send a GET request to this /heartbeat/all to get
	how much time has passed since nodes last sent a heartbeat.
	"""
	s = 'the last heartbeat of nodes are:\n'
	now = time.time ()
	for name in heartbeat:
		_time = now - heartbeat [name]
		s = s + name + ' was ' + str (_time) + ' seconds ago. ' \
		    + 'it should be less than 30s.\n'
	return s


@app.route ('/heartbeat/abnormal', methods=['GET'])
def route_abnormal_heartbeat ():
	"""
	you can send a GET request to this /heartbeat/abnormal to get
	the likely abnormal nodes.
	"""
	s = 'the last heartbeat of likely abnormal nodes are:\n'
	now = time.time ()
	for name in heartbeat:
		_time = now - heartbeat [name]
		if _time > 30:
			s = s + name + ' was ' + str (_time) + ' seconds ago. ' \
			    + 'it should be less than 30s.\n'
	return s


@app.route ('/docker/address', methods=['GET'])
def route_docker_address ():
	"""
	this function can listen tc settings from controller/ctl_utils.py, send_docker_address ().
	save ip of ctl..
	"""
	global ctl_addr
	ctl_addr = request.args.get ('address')
	return ''


@app.route ('/docker/tc', methods=['POST'])
def route_docker_tc ():
	"""
	this function can listen tc settings from controller/ctl_utils.py, send_docker_tc ().
	after containers are ready, it will deploy containers' tc settings.
	"""
	data = json.loads (request.form ['data'])
	print (data)
	tc_data.update (data)
	return ''


@app.route ('/docker/build', methods=['POST'])
def route_docker_build ():
	"""
	this function can listen files from controller/ctl_utils.py, deploy_dockerfile ().
	it will use these files to build a docker image.
	"""
	path = os.path.join (dirname, 'Dockerfile')
	request.files.get ('Dockerfile').save (path)
	request.files.get ('dml_req').save (os.path.join (dirname, 'dml_req.txt'))
	tag = request.form ['tag']
	cmd = 'sudo docker build -t ' + tag + ' -f ' + path + ' .'
	print (cmd)
	p = sp.Popen (cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
	msg = p.communicate () [0].decode ()
	print (msg)
	if 'Successfully tagged' in msg:
		print ('build image succeed')
		return '1'
	else:
		print ('build image failed')
		return '-1'


@app.route ('/docker/start', methods=['POST'])
def route_docker_start ():
	"""
	this function can listen message from controller/ctl_utils.py, deploy_yml ().
	it will deploy the yml file.
	"""
	heartbeat.clear ()
	filename = os.path.join (dirname, hostname + '.yml')
	request.files.get ('yml').save (filename)
	s = ''
	with open (filename, 'r') as f:
		for line in f:
			if '0xffff' in line:
				# change the 0xffff in NET_AGENT_ADDRESS to port.
				line = line.replace ('0xffff', str (agent_port))
			s += line
	with open (filename, 'w')as f:
		f.write (s)
	cmd = 'sudo docker-compose -f ' + filename + ' up'
	print (cmd)
	sp.Popen (cmd, shell=True, stderr=sp.STDOUT)
	return ''


@app.route ('/docker/stop', methods=['GET'])
def route_docker_stop ():
	"""
	this function can listen message from controller/ctl_utils.py, stop_yml ().
	it will stop the above yml file.
	"""
	cmd = 'sudo docker-compose -f ' + hostname + '.yml stop'
	print (cmd)
	sp.Popen (cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait ()
	heartbeat.clear ()
	return ''


@app.route ('/docker/clear', methods=['GET'])
def route_docker_clear ():
	"""
	this function can listen message from controller/ctl_utils.py, clear_yml ().
	it will clear the above yml file.
	"""
	cmd = 'sudo docker-compose -f ' + hostname + '.yml down -v'
	print (cmd)
	sp.Popen (cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait ()
	heartbeat.clear ()
	return ''


@app.route ('/docker/reset', methods=['GET'])
def route_docker_reset ():
	"""
	this function can listen message from controller/ctl_utils.py, reset_docker ().
	it will remove all docker containers, networks and volumes.
	"""
	cmd = ['sudo docker rm -f $(docker ps -aq)',
	       'sudo docker network rm $(docker network ls -q)',
	       'sudo docker volume rm $(docker volume ls -q)']
	for c in cmd:
		print (c)
		sp.Popen (c, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait ()
	heartbeat.clear ()
	return ''


@app.route ('/device/nfs', methods=['POST'])
def route_device_nfs ():
	"""
	this function can listen nfs settings from controller/ctl_utils.py, send_device_nfs ().
	it will mount the nfs path.
	"""
	route_device_clear_nfs ()
	mounted = ''
	data = json.loads (request.form ['data'])
	print (data)
	ip = data ['ip']
	nfs = data ['nfs']
	err = []
	for nfs_path in nfs:
		local_path = nfs [nfs_path]
		# is relative path.
		if local_path [0] != '/':
			local_path = os.path.abspath (os.path.join (dirname, local_path))
		if not os.path.exists (local_path):
			os.makedirs (local_path)
		cmd = 'sudo mount -t nfs ' + ip + ':' + nfs_path + ' ' + local_path
		print (cmd)
		p = sp.Popen (cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
		msg = p.communicate () [0].decode ()
		if msg == '':
			print ('mount nfs succeed')
			mounted += local_path + '\n'
		else:
			print ('mount nfs failed, err:')
			print (msg)
			err.append (msg)

	# record the path of mounted.
	with open (os.path.join (dirname, 'mounted.txt'), 'w') as f:
		f.write (mounted)
	return json.dumps (err)


@app.route ('/device/tc', methods=['POST'])
def route_device_tc ():
	"""
	this function can listen tc settings from controller/ctl_utils.py, send_device_tc ().
	it will apply the tc settings.
	"""
	data = json.loads (request.form ['data'])
	print (data)
	tc = data ['NET_NODE_TC']
	nic = tc_data ['NET_NODE_NIC']
	prefix = 'sudo '
	clear_tc_helper (prefix, nic)
	if tc:
		tc_ip = data ['NET_NODE_TC_IP']
		tc_port = data ['NET_NODE_TC_PORT']
		cmd = deploy_tc_helper (prefix, nic, tc, tc_ip, tc_port)
		p = sp.Popen (' && '.join (cmd), stdout=sp.PIPE, stderr=sp.STDOUT, shell=True, close_fds=True)
		msg = p.communicate () [0].decode ()
		if msg != '':
			print ('tc failed, err:')
			print (msg)
			return msg

	print ('tc succeed')
	return '1'


def clear_tc_helper (prefix: str, nic: str):
	cmd = prefix + ' tc qdisc show dev %s' % nic
	p = sp.Popen (cmd, stdout=sp.PIPE, stderr=sp.STDOUT, shell=True)
	msg = p.communicate () [0].decode ()
	if "priomap" not in msg and "noqueue" not in msg:
		cmd = prefix + ' tc qdisc del dev %s root' % nic
		sp.Popen (cmd, stdout=sp.PIPE, stderr=sp.STDOUT, shell=True).wait ()


def deploy_tc_helper (prefix: str, nic: str, tc: Dict [str, str], tc_ip: Dict [str, str],
		tc_port: Dict [str, List [int]]):
	cmd = ['%s tc qdisc add dev %s root handle 1: htb default 1' % (prefix, nic),
	       '%s tc class add dev %s parent 1: classid 1:1 htb rate 10gbps ceil 10gbps burst 15k' % (prefix, nic)]
	i = 10
	for name in tc.keys ():
		ip = tc_ip [name]
		bw = tc [name]
		cmd.append ('%s tc class add dev %s parent 1:1 classid ' % (prefix, nic)
		            + '1:%d htb rate %s ceil %s burst 15k' % (i, bw, bw))
		if name in tc_port:
			# is a container.
			# all ports of this container share the same limit.
			for port in tc_port [name]:
				cmd.append ('%s tc filter add dev %s protocol ip parent 1: prio 2 u32 match ip dst ' % (prefix, nic)
				            + '%s/32 match ip dport %d 0xffff flowid 1:%d' % (ip, port, i))
		else:
			# is a device.
			cmd.append ('%s tc filter add dev %s protocol ip parent 1: prio 2 u32 match ip dst ' % (prefix, nic)
			            + '%s/32 flowid 1:%d' % (ip, i))
		i += 1
	return cmd


@app.route ('/device/env', methods=['POST'])
def route_device_env ():
	"""
	this function can listen env from controller/ctl_utils.py, send_device_env ().
	it will save the env.
	"""
	atexit.register (route_device_reset)
	global ctl_addr
	data = json.loads (request.form ['data'])
	print (data)
	env = data ['NET_NODE_ENV']
	ctl_addr = env ['NET_CTL_ADDRESS'] = data ['NET_CTL_ADDRESS']
	tc_data ['NET_NODE_NIC'] = data ['NET_NODE_NIC']
	env ['NET_AGENT_ADDRESS'] = data ['NET_AGENT_IP'] + ':' + str (agent_port)
	env ['NET_NODE_NAME'] = data ['NET_NODE_NAME']
	for k in env:
		os.environ [k] = env [k]
	return ''


@app.route ('/device/req', methods=['POST'])
def route_device_req ():
	"""
	this function can listen dml_req.txt from controller/ctl_utils.py, sent_device_req ().
	it will install the dml_req.txt by pip.
	"""
	path = os.path.join (dirname, 'dml_req.txt')
	request.files.get ('dml_req').save (path)
	# double check it because you should probably run
	# [pip install] or [sudo pip install] or [pip3 install] instead of this default one.
	cmd = 'sudo pip3 install -r ' + path
	print (cmd)
	sp.Popen (cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait ()
	# if the above installation is successful, it will output {package==version}.
	cmd = 'sudo pip3 freeze -r ' + path
	print (cmd)
	p = sp.Popen (cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
	msg = p.communicate () [0].decode ()
	# just need the packages in dml_req.txt.
	msg = msg [:msg.find ('#')].upper ()
	req = []
	err = []
	with open (path, 'r')as f:
		for line in f:
			if line.rfind ('=') != -1:
				line = line [:line.rfind ('=') - 1]
			req.append (line.replace ('\r', '').replace ('\n', '').upper ())
	for r in req:
		if r not in msg:
			err.append (r)
	if err:
		print ('req failed, err:')
		print (err)
		return json.dumps (err)
	else:
		print ('req succeed')
		return '1'


@app.route ('/device/start', methods=['POST'])
def route_device_start ():
	"""
	this function can listen message from controller/ctl_utils.py, deploy_device ().
	it will start a new process to execute the ${cmd} at ${working_dir}.
	"""
	global dml_p
	data = json.loads (request.form ['data'])
	working_dir = data ['dir']
	# is relative path.
	if working_dir [0] != '/':
		working_dir = os.path.abspath (os.path.join (dirname, working_dir))
	cmd = ' '.join (data ['cmd'])
	print ('CWD ' + working_dir + ' RUN ' + cmd)
	dml_p = sp.Popen (cmd, cwd=working_dir, shell=True, stderr=sp.STDOUT)
	return ''


@app.route ('/device/stop', methods=['GET'])
def route_device_stop ():
	"""
	this function can listen message from controller/ctl_utils.py, stop_device ().
	it will kill the process started by above route_device_start ().
	"""
	try:
		if dml_p.poll () is None:
			# ${dml_p.pid} is the pid of the shell process,
			# because we use shell to execute the ${cmd}.
			# in most cases, the pid of ${cmd} is ${dml_p.pid}+1,
			# so we just try to terminate ${dml_p.pid}+1.
			# hopefully we don't terminate other processes by mistake :-)
			os.kill (dml_p.pid + 1, 3)
	except  NameError:
		pass
	finally:
		return ''


@app.route ('/device/clear/tc', methods=['GET'])
def route_device_clear_tc ():
	"""
	this function can listen message from controller/ctl_utils.py, clear_device_tc ().
	it will reset tc settings.
	"""
	if 'NET_NODE_NIC' in tc_data:
		clear_tc_helper ('sudo ', tc_data ['NET_NODE_NIC'])
	return ''


@app.route ('/device/clear/nfs', methods=['GET'])
def route_device_clear_nfs ():
	"""
	this function can listen message from controller/ctl_utils.py, clear_device_nfs ().
	it will reset nfs.
	"""
	path = os.path.join (dirname, 'mounted.txt')
	if os.path.exists (path):
		with open (path, 'r') as f:
			for line in f:
				cmd = 'sudo umount -t nfs -l ' + line
				print (cmd)
				sp.Popen (cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait ()
	return ''


@app.route ('/device/reset', methods=['GET'])
def route_device_reset ():
	"""
	this function can listen message from controller/ctl_utils.py, reset_device ().
	it will kill the process started by above route_device_start (),
	reset tc settings and reset nfs.
	"""
	route_device_stop ()
	if 'NET_NODE_NIC' in tc_data:
		clear_tc_helper ('sudo ', tc_data ['NET_NODE_NIC'])
	route_device_clear_nfs ()
	return ''


@app.route ('/docker/tc/update', methods=['POST'])
def route_docker_tc_update ():
	"""
	this function can listen tc settings from controller/ctl_utils.py, send_docker_tc ().
	after containers are ready, it will deploy containers' tc settings.
	"""
	data = json.loads (request.form ['data'])
	ret = {}
	tasks = []
	for name in data:
		tc = data [name] ['NET_NODE_TC']
		nic = data [name] ['NET_NODE_NIC']
		prefix = 'sudo docker exec ' + name + ' '
		clear_tc_helper (prefix, nic)
		if tc:
			tc_ip = data [name] ['NET_NODE_TC_IP']
			tc_port = data [name] ['NET_NODE_TC_PORT']
			cmd = deploy_tc_helper (prefix, nic, tc, tc_ip, tc_port)
			tasks.append (executor.submit (docker_tc_update_helper, ret, cmd, name, len (tc)))
		else:
			ret [name] = {}
	wait (tasks, return_when=ALL_COMPLETED)
	return json.dumps (ret)


def docker_tc_update_helper (ret, cmd, name, number):
	p = sp.Popen (' && '.join (cmd), stdout=sp.PIPE, stderr=sp.STDOUT, shell=True, close_fds=True)
	msg = p.communicate () [0].decode ()
	if msg != '':
		print (name + ' update tc failed, err:')
		print (msg)
		ret [name] = {'number': '-1', 'msg': msg}
	else:
		print (name + ' update tc succeed')
		ret [name] = {'number': str (number)}


@app.route ('/device/tc/update', methods=['POST'])
def route_device_tc_update ():
	"""
	this function can listen tc settings from controller/ctl_utils.py, update_device_tc ().
	it will clear the old tc settings and apply the new one.
	"""
	data = json.loads (request.form ['data'])
	tc = data ['NET_NODE_TC']
	nic = tc_data ['NET_NODE_NIC']
	prefix = 'sudo '
	clear_tc_helper (prefix, nic)
	if tc:
		tc_ip = data ['NET_NODE_TC_IP']
		tc_port = data ['NET_NODE_TC_PORT']
		cmd = deploy_tc_helper (prefix, nic, tc, tc_ip, tc_port)
		p = sp.Popen (' && '.join (cmd), stdout=sp.PIPE, stderr=sp.STDOUT, shell=True, close_fds=True)
		msg = p.communicate () [0].decode ()
		if msg != '':
			return msg

	print (' update tc succeed')
	return '1'


app.run (host='0.0.0.0', port=agent_port, threaded=True)
