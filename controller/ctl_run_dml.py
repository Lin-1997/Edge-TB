import os

from flask import Flask

import ctl_utils
from dml.dml_listener import listener
from class_node import Net


def on_tc_ready ():
	print ('tc ready')


if __name__ == '__main__':
	ip = '192.168.2.10'
	port = 9000
	net = Net (ip + ':' + str (port))

	cList = []

	start_id = 1
	cs1 = net.add_container_server ('se-lab-3700x', '192.168.2.5')
	for i in range (5):
		cList.append (cs1.add_container ('n' + str (i + start_id), 'eth0', '/home/worker',
			['bash', 'run-dml.sh'], 'dml:v1.0', cpu=3, memory=9, unit='Gi'))
		cList [i + start_id - 1].add_envs ({'NAME': 'n' + str (i + start_id), 'PORT': str (8000 + i + start_id)})
		cList [i + start_id - 1].add_volume ('/home/lin/Desktop/net/worker', '/home/worker')
		cs1.add_port (cList [i + start_id - 1], 8000 + i + start_id, svc_node_port=30000 + i + start_id)

	start_id = 6
	cs2 = net.add_container_server ('se-lab-3990x', '192.168.2.8')
	for i in range (25):
		cList.append (cs2.add_container ('n' + str (i + start_id), 'eth0', '/home/worker',
			['bash', 'run-dml.sh'], 'dml:v1.0', cpu=5, memory=9, unit='Gi'))
		cList [i + start_id - 1].add_envs ({'NAME': 'n' + str (i + start_id), 'PORT': str (8000 + i + start_id)})
		cList [i + start_id - 1].add_volume ('/home/lin/Desktop/net/worker', '/home/worker')
		cs2.add_port (cList [i + start_id - 1], 8000 + i + start_id, svc_node_port=30000 + i + start_id)

	for i in range (29):
		for j in range (29 - i):
			net.dual_link_limit (cList [i], cList [i + j + 1], bw=10, unit='mbps')

	dirname = os.path.abspath (os.path.dirname (__file__))
	net.save_yml (dirname)
	net.deploy_yml (dirname)

	app = Flask (__name__)

	ctl_utils.tc_listener (app, net, on_tc_ready)
	ctl_utils.print_listener (app)
	ctl_utils.send_device_conf (net)

	listener (app)

	app.run (host='0.0.0.0', port=port, threaded=True)
