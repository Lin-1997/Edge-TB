import os

from flask import Flask

import ctl_utils
from class_node import Net

# we made up the following physical hardware so this example is NOT runnable.
if __name__ == '__main__':
	# ip of this computer.
	ip = '192.168.1.10'
	# port of this Flask server.
	port = 9000
	net = Net (ip + ':' + str (port))
	# path of this file
	dirname = os.path.abspath (os.path.dirname (__file__))

	# define your network >>>

	# declare a container server, which should be added to the k8s network in advance.
	cs1 = net.add_container_server (name='server-1', ip='192.168.1.11')

	# add a container to a container server, which will be done after you run this python code.
	# the total cpu and memory resources can not exceed the resources owned by the server.
	# the container uses at most cpu=[] CPU cores (more accurately threads).
	# if the container asks for more than memory=[] memory, it will be killed by k8s.
	# see https://kubernetes.io/docs/tasks/configure-pod-container/ for more.
	c1 = net.add_container (server=cs1, name='n1', nic='eth0', working_dir='/path/in/container',
		cmd=['bash', 'run-example.sh'], image='some_image:v1', cpu=3, memory=1, unit='Gi')
	c1.add_envs ({'key': 'value'})
	c1.add_volume (host_path='path/in/server-1', mount_path='/path/in/container')
	# use a same svc_port as container_port.
	cs1.add_port (c1, container_port=8001, svc_node_port=30001)

	# add many containers
	start_id = 2
	cs2 = net.add_container_server ('server-2', '192.168.1.12')
	cList = []
	for i in range (3):
		cList.append (net.add_container (cs2, 'n' + str (i + start_id), 'eth0', '/path/in/container',
			['bash', 'run-example.sh'], 'some_image:v1', cpu=1))
		cList [i].add_envs ({'key': 'value'})
		cList [i].add_volume ('path/in/server-2', '/path/in/container')
		cs2.add_port (cList [i], container_port=8000 + i + start_id, svc_port=9000 + i + start_id,
			svc_node_port=30000 + i + start_id)

	# declare a device (e.bw_array., Raspberry Pi), which should already exist.
	# you should run the worker/worker_tc_init.py in your devices,
	# which is a Flask server listening for the TC settings and envs,
	# before you run this python code.
	d1 = net.add_device (name='d1', nic='eth0', ip='192.168.1.13')
	d1.add_envs ({'key': 'value'})

	# save the node's information as node_ip.txt file in json format.
	# the parameter should be just a directory without file name.
	net.save_node_ip (dirname)

	# declare a upper limit of bandwidth from one node to another,
	# or between two nodes through Linux Traffic Control.
	# net.single_link_limit (c1, cList [0], bw=500, unit='kbps')
	# net.dual_link_limit (d1, cList [1], bw=2, unit='mbps')

	# if you set the TC settings manually,
	# you can save them as bw.txt file in json format,
	# and load it by load_bw () in the next time.
	# the parameter should be just a directory without file name.
	# net.save_bw (dirname)

	# if you have a large number of densely connected nodes,
	# we recommend using load_bw ().
	# we cannot set the bandwidth between two nodes twice,
	# so we comment out the above single_link_limit () and dual_link_limit ().

	# load TC settings from file.
	bw_json = ctl_utils.read_json (os.path.join (dirname, 'bw.txt'))
	net.load_bw (bw_json ['order'], bw_json ['bw'])
	"""
	the contents in this example bw.txt are:
	
	{"order": ["n1", "n2", "n3", "n4", "d1"],
	"bw": [["inf", "4969kbps", "2096kbps", "3326kbps", "2245kbps"], (row1)
	["3656kbps", "inf", "4091kbps", "None", "3971kbps"],
	["2996kbps", "3368kbps", "inf", "2683kbps", "None"],
	["3195kbps", "None", "4131kbps", "inf", "2295kbps"],
	["2395kbps", "4280kbps", "None", "3648kbps", "inf"]]}
	
	we parse this file like this:
	row1 in bw means: n1--inf-->n1, n1--4969kbps-->n2...
	row4 in bw means: n4--3195kbps-->n1, n4--without link_limit ()-->n2...

	the bandwidth between two nodes that without link_limit () depends on
	your physical network, and we will not block the network connection between them.
	
	we recommend you to treat two nodes without link_limit () as if
	they are not connected to each other.
	
	if you want to limit bandwidth between nodes with our link_limit (),
	you should run the worker/worker_tc_init.py in your containers and devices
	before running your apps.
	we recommend using the following file structure in your containers and devices,
	and use ['bash', 'run-app.sh'] as enter command of your containers and devices.
	
	./worker
	├── run-app.sh
	├── worker_tc_init.py
	├── ...
	└── your_app_folder
            ├── app.java
            ├── ...
            └── run.sh

	in run-app.sh:
		python3 worker_tc_init.py
		cd your_app_folder
		bash run.sh
	
	in run.sh:
		javac app.java
		java app
	"""

	# <<< define your network

	app = Flask (__name__)

	# containers will post requests to here for the TC settings.
	# here we use GET at '/tc' and route_tc (), GET at 'tcReady' and route_tc_ready ().
	# if you don't have any container or any limited link between containers,
	# just comment out it.
	ctl_utils.tc_listener (app, net)

	# here we use POST at '/print' and route_print ().
	ctl_utils.print_listener (app)

	# here we use GET at '/heartbeat' and route_heartbeat (),
	# GET at '/all_heartbeat' and route_all_heartbeat ()
	# and GET at '/abnormal_heartbeat' and route_abnormal_heartbeat ().
	ctl_utils.heartbeat_listener (app)

	# add whatever listeners you want here, but don’t have the same names as we already use.
	# @app.route ('/func', methods=['POST'])
	# def route_func ():
	# 	pass

	# send the TC settings and envs to devices.
	# devices should running the worker/worker_tc_init.py in advance.
	# if you don't have any device, just comment out it.
	ctl_utils.send_device_conf (net)

	# save the deployment of containers as k8s yml file.
	# the parameter should be just a directory without file name.
	net.save_k8s_yml (dirname)
	# deploy the k8s yml file.
	# the parameter should be just a directory without file name.
	net.deploy_k8s_yml (dirname)

	app.run (host='0.0.0.0', port=port, threaded=True)
