import os

from flask import Flask

import ctl_utils
from class_node import Net


# this function will be executed after all containers and devices have completed TC settings.
def on_tc_ready ():
	# whatever your want.
	pass


# we made up the following physical hardware so this example is NOT runnable.
if __name__ == '__main__':
	# ip of this computer.
	ip = '192.168.1.10'
	# port of this Flask server.
	port = 9000
	net = Net (ip + ':' + str (port))

	# define your network >>>

	# declare a container server, which should be added to the k8s network in advance.
	cs1 = net.add_container_server (name='server-1', ip='192.168.1.11')

	# add a container to this container server, which will be done after you run this python code.
	# the total cpu and memory resources can not exceed the resources owned by the server,
	# see https://kubernetes.io/docs/tasks/configure-pod-container/ for more.
	c1 = cs1.add_container (name='n1', nic='eth0', working_dir='/path/in/container',
		cmd=['bash', 'run-example.sh'], image='some_image:v1', cpu=3, memory=1, unit='Gi')
	c1.add_envs ({'key': 'value'})
	c1.add_volume (host_path='path/in/server-1', mount_path='/path/in/container')
	# use a same svc_port as container_port.
	cs1.add_port (c1, container_port=8001, svc_node_port=30001)

	# add many containers
	start_id = 2
	cs2 = net.add_container_server ('server-2', '192.168.1.12')
	cList = []
	for i in range (5):
		cList.append (cs2.add_container ('n' + str (i + start_id), 'eth0', '/path/in/container',
			['bash', 'run-example.sh'], 'some_image:v1', cpu=1))
		cList [i].add_envs ({'key': 'value'})
		cList [i].add_volume ('path/in/server-2', '/path/in/container')
		cs2.add_port (cList [i + start_id - 1], container_port=8000 + i + start_id,
			svc_port=9000 + i + start_id, svc_node_port=30000 + i + start_id)

	# declare a device (e.g., Raspberry Pi), which should already exist.
	# you should run the worker/worker_tc_init.py in your devices,
	# which is a Flask server listening for the TC settings and envs,
	# before you run this python code.
	d1 = net.add_device (name='d1', nic='eth0', ip='192.168.1.13')
	d1.add_envs ({'key': 'value'})

	# TODO 单向tc限制

	# declare a upper limit of bandwidth between two nodes through Linux Traffic Control.
	# it cannot guarantee the lower limit.
	net.add_link_limit (c1, cList [0], bw=500, unit='kbps')
	net.add_link_limit (d1, cList [3], bw=2, unit='mbps')
	# the bandwidth between two nodes that WITHOUT add_link_limit () depends on your physical network.
	# we will NOT block the network connection between them.

	"""
	if you want to limit bandwidth between nodes with our Net.add_link_limit (),
	you should run the worker/worker_tc_init.py in your containers and devices before running your apps.
	we recommend using the following file structure in your containers and devices:
	
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

	dirname = os.path.abspath (os.path.dirname (__file__))
	# save the deployment of containers as yml file.
	net.save_yml (dirname)
	# deploy yml file.
	net.deploy_yml (dirname)

	app = Flask (__name__)

	# containers will post requests to here for the TC settings.
	# here we use POST at '/tc' and route_tc (), GET at 'tcReady' and route_tc_ready ().
	# if you don't have any container or any limited link between containers,
	# just comment out it.
	ctl_utils.tc_listener (app, net, on_tc_ready)

	# here we use POST at '/print' and route_print ().
	ctl_utils.print_listener (app)

	# send the TC settings and envs to devices.
	# devices should running the worker/worker_tc_init.py in advance.
	# if you don't have any device, just comment out it.
	ctl_utils.send_device_conf (net)

	# add whatever listeners you want here, but don’t have the same names as we already use.
	# @app.route ('/func', methods=['POST'])
	# def route_func ():
	# 	pass

	app.run (host='0.0.0.0', port=port, threaded=True)
