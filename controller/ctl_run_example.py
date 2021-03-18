import os

from flask import Flask

import ctl_utils
import dml_listener
from class_node import Net

# we made up the following physical hardware so this example is NOT runnable.
if __name__ == '__main__':
	# path of this file.
	dirname = os.path.abspath (os.path.dirname (__file__))
	# ip of this ctl.
	ip = '192.168.1.10'
	# port of this Flask server.
	port = 3333
	net = Net (ip, port)
	# declare a nfs read-only absolute path in this ctl.
	net.add_nfs (tag='dml_app', ip='192.168.1.0', mask=24,
		path='/path/in/ctl/to/controller/dml_app')
	# export the path through nfs.
	ctl_utils.export_nfs (net)

	# in dml, the node name starts with a letter, followed by numbers, e.g., n1, n2, d1.
	# containers listen on port 4444, and map port 4444 to host port 8000+x,
	# where x is the numeric part of the name, e.g., n1 map port 4444 to host port 8001.
	# devices listen on port 4444.
	# with these rules, we can use controller/dml_tool/conf_generator.py
	# to quickly generate the  ip:port part of env files for each container and device.
	# we do not recommend changing this port number, but if you really want to change it,
	# you need to change controller/dml_app/etree_learning.py, controller/dml_app/dml_listener.py,
	# controller/class_node.py, controller/dml_tool/conf_generator.py together.
	dml_port = 4444

	# define your network >>>

	# store containers.
	cList = []

	# declare a container server, which should run the worker/agent.py in advance.
	cs1 = net.add_container_server (name='server-1', ip='192.168.1.11')

	# make the nfs shared path in this ctl available for containers in a container server.
	# container server's ip should in the subnet of ${ip/mask} defined in above add_nfs ().
	cs1.mount_nfs (tag='dml_app')

	# add a container to a container server, which will be done after you run this python code.
	# the total cpu and memory resources can not exceed the resources owned by the server.
	# the container uses at most ${cpu} CPU cores (more accurately threads).
	# if the container asks for more than ${memory unit} memory, it will be killed.
	cList.append (cs1.add_container (name='n1', nic='eth0', working_dir='/home/worker/dml_app',
		cmd=['python3', 'etree_learning.py'], image='dml:v1.0', cpu=3, memory=5, unit='G'))
	# ${host_path} can use absolute path starting from / or
	# relative path starting from the directory of the worker/agent.py file.
	# ${container_path} can only use absolute path starting from /.
	cList [0].add_volume (host_path='/path/in/server-1/to/worker/dml_file',
		container_path='/home/worker/dml_file')
	# ${container_path} can only use absolute path starting from /.
	cList [0].add_nfs (tag='dml_app', container_path='/home/worker/dml_app')
	cList [0].add_port (port=dml_port, host_port=8001)

	# add many containers.
	start_id = 2
	cs2 = net.add_container_server ('server-2', '192.168.1.12')
	cs2.mount_nfs ('dml_app')
	for i in range (3):
		cList.append (cs2.add_container ('n' + str (i + start_id), 'eth0', '/home/worker/dml_app',
			['python3', 'etree_learning.py'], 'dml:v1.0', cpu=5, memory=5, unit='G'))
		# ${host_path} means /path/in/server-2/to/worker/dml_file in this example.
		cList [i + start_id - 1].add_volume ('./dml_file', '/home/worker/dml_file')
		cList [i + start_id - 1].add_nfs ('dml_app', '/home/worker/dml_app')
		cList [i + start_id - 1].add_port (dml_port, 8000 + i + start_id)

	# declare a device (e.g., Raspberry Pi),
	# which should run the worker/agent.py in advance.
	d1 = net.add_device (name='d1', nic='eth0', ip='192.168.1.13')
	# device's ip should in the subnet of ${ip/mask} defined in above add_nfs ().
	# ${mount_point} can use absolute path starting from / or
	# relative path starting from the directory of the worker/agent.py file.
	# ${mount_point} means /path/in/d1/to/worker/dml_app in this example.
	d1.mount_nfs (tag='dml_app', mount_point='./dml_app')
	# set device's task.
	# ${working_dir} can use absolute path or relative path as above mount_nfs ().
	d1.set_cmd (working_dir='dml_app', cmd=['python3', 'etree_learning.py'])

	# save the node's information as node_ip.txt file in json format.
	# the path should be just a directory without file name.
	net.save_node_ip (dirname)

	# add a link with limited bandwidth from one node to another,
	# or between two nodes through Linux Traffic Control.
	# net.single_link_limit (cList [0], cList[2], bw=500, unit='kbps')
	# net.dual_link_limit (d1, cList [1], bw=2, unit='mbps')

	# if you set the tc settings manually,
	# you can save them as bw.txt file in json format,
	# and load it by load_bw () in the next time.
	# the path should be just a directory without file name.
	# net.save_bw (dirname)

	# if you have a large number of densely connected nodes,
	# we recommend using load_bw ().
	# we cannot set the bandwidth between two nodes twice,
	# so we comment out the above single_link_limit () and dual_link_limit ().

	# use controller/random_topology.py to generate a bw.txt in advance.
	# load tc settings from bw.txt.
	bw_json = ctl_utils.read_json (os.path.join (dirname, 'bw.txt'))
	net.load_bw (bw_json ['order'], bw_json ['bw'])
	"""
	the contents in this example bw.txt are:
	
	{"order": ["n1", "n2", "n3", "n4", "d1"],
	"bw": {"n1": ["inf", "4mbps", "512kbps", "3mbps", "512kbps"],
	"n2": ["3mbps", "inf", "4mbps", "None", "512kbps"],
	"n3": ["512kbps", "3mbps", "inf", "1mbps", "None"],
	"n4": ["2mbps", "None", "1mbps", "inf", "2mbps"],
	"d1": ["256kbps", "256kbps", "None", "1mbps", "inf"]}}
	
	we parse this file like this:
	row1 in bw means: n1--inf-->n1, n1--4mbps-->n2...
	row4 in bw means: n4--2mbps-->n1, n4--1bps-->n2...

	0bps, 0kbps... are not allowed in Linux Traffic Control, so we set 1bps to 
	block the network connection between two nodes with "None" connection.
	
	it takes a while to deploy the tc settings.
	when the terminal prints "tc finish", tc settings of all containers and devices are deployed.
	please make sure your node communicate with other nodes after "tc finish".
	"""

	# save the deployment of containers as ${containerServer.name}.yml file.
	# the path should be just a directory without file name.
	net.save_yml (dirname)

	# <<< define your network

	app = Flask (__name__)

	# here we use POST at '/print'.
	ctl_utils.print_listener (app)

	# here we use POST at '/docker/tc'.
	ctl_utils.docker_tc_listener (app, net)
	# send ctl's ${ip:port} to the agent of container servers.
	ctl_utils.send_docker_address (net)
	# send the tc settings to the agent of container servers.
	ctl_utils.send_docker_tc (net)
	# send the Dockerfile and dml_req.txt to the agent of container servers.
	# the path should be just a directory.
	# no need to call this function every time, unless you need to build a new docker image.
	path_dockerfile = os.path.join (dirname, 'dml_app/Dockerfile')
	path_req = os.path.join (dirname, 'dml_app/dml_req.txt')
	ctl_utils.deploy_dockerfile (net, 'dml:v1.0', path_dockerfile, path_req)

	# send the nfs settings to devices.
	ctl_utils.send_device_nfs (net)
	# send the tc settings to devices.
	ctl_utils.send_device_tc (net)
	# send the envs to devices.
	# we have added some env by default, so you need to call this function
	# even if you don’t add custom env.
	ctl_utils.send_device_env (net)
	# send the dml_req.txt to devices.
	# the path should be just a directory.
	# no need to call this function every time, unless you need to install some new packages.
	ctl_utils.sent_device_req (net, path_req)

	# here we use GET at '/update/tc'
	ctl_utils.update_tc_listener (app, net)
	"""
	you can send a GET request to ctl's /update/tc at any time
	to update the tc settings of containers and/or devices. 

	for example, curl http://192.168.1.10:3333/update/tc?path=bw2.txt
	the contents in this example bw2.txt are:

	{"order": ["n1", "n2", "n3", "n4", "d1"],
	"bw": {"n1": ["inf", "2mbps", "2mbps", "3mbps", "512kbps"],
	"d1": ["1mbps", "1mbps", "None", "2mbps", "inf"]}}

	we will clear the tc settings of n1 and d1 and deploy the new one dynamically
	without stop the containers or devices.
	for the above reasons, even if the bw from n1 to n4 does not change,
	it needs to be specified.
	"""

	# when you finish your experiments, you should restore your container servers and devices.
	# first restore container servers, then restore devices, and finally restore ctl's nfs.
	# here we use GET at '/docker/stop', '/docker/clear' and '/docker/reset'.
	ctl_utils.docker_controller_listener (app, net)
	# here we use GET at '/device/stop', '/device/clear/tc', '/device/clear/nfs' and 'device/reset'.
	ctl_utils.device_controller_listener (app, net)
	# here we use GET at '/clear/nfs'.
	ctl_utils.clear_nfs_listener (app)

	# add whatever listeners you want here,
	# but don’t have the same names as we already use.
	# @app.route ('/func', methods=['POST'])
	# def route_func ():
	# 	pass
	# we will stop all devices and clear all containers if everything goes well in dml_listener.
	dml_listener.listener (app, net)

	# send the cmd to the agent of devices.
	ctl_utils.deploy_all_device (net)
	# send the yml files to the agent of container servers.
	# the path should be the same as above save_yml ().
	ctl_utils.deploy_all_yml (net, dirname)

	app.run (host='0.0.0.0', port=port, threaded=True)
