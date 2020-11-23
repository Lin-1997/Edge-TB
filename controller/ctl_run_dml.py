import os

from flask import Flask

import ctl_utils
from dml import dml_listener
from class_node import Net

# we made up the following physical hardware so this example is NOT runnable.
if __name__ == '__main__':
	ip = '192.168.1.10'
	port = 9000
	net = Net (ip + ':' + str (port))
	dirname = os.path.abspath (os.path.dirname (__file__))

	# in dml, containers are named like n1, n2, and device are named like d1, d2.
	# containers listen on port 8000+x {x means the numeric part of the name}, e.g., n1 listens on 8001.
	# k8s maps port 30000+x to port 8000+x of the container,
	# e.g., messages to k8s's port 30001 will be forward to n1's port 8001.
	# devices listen on port 8888.
	# with these rules, we can use controller/dml/conf_env_gen.py
	# to quickly generate the ip:port part of env files for each container and device.
	cList = []
	cs1 = net.add_container_server (name='server-1', ip='192.168.1.11')
	cList.append (net.add_container (cs1, 'n1', 'eth0', '/home/worker',
		['bash', 'run-dml.sh'], 'dml:v1.0', cpu=3, memory=5, unit='Gi'))
	cList [0].add_envs ({'NAME': 'n1', 'PORT': str (8001)})
	cList [0].add_volume ('/path/in/server-1/worker', '/home/worker')
	cs1.add_port (cList [0], 8001, svc_node_port=30001)

	start_id = 2
	cs2 = net.add_container_server ('server-2', '192.168.1.12')
	for i in range (3):
		cList.append (net.add_container (cs2, 'n' + str (i + start_id), 'eth0', '/home/worker',
			['bash', 'run-dml.sh'], 'dml:v1.0', cpu=5, memory=5, unit='Gi'))
		cList [i + start_id - 1].add_envs ({'NAME': 'n' + str (i + start_id), 'PORT': str (8000 + i + start_id)})
		cList [i + start_id - 1].add_volume ('/path/in/server-2/worker', '/home/worker')
		cs2.add_port (cList [i + start_id - 1], 8000 + i + start_id, svc_node_port=30000 + i + start_id)

	d1 = net.add_device (name='d1', nic='eth0', ip='192.168.1.13')
	d1.add_envs ({'NAME': 'd1', 'PORT': str (8888)})

	net.save_node_ip (dirname)

	# use controller/tools/random_bw.py to generate a bw.txt in advance.
	bw_json = ctl_utils.read_json (os.path.join (dirname, 'bw.txt'))
	net.load_bw (bw_json ['order'], bw_json ['bw'])

	app = Flask (__name__)

	ctl_utils.tc_listener (app, net)
	ctl_utils.print_listener (app)
	ctl_utils.heartbeat_listener (app)

	dml_listener.listener (app)

	ctl_utils.send_device_conf (net)

	net.save_k8s_yml (dirname)
	net.deploy_k8s_yml (dirname)

	app.run (host='0.0.0.0', port=port, threaded=True)
