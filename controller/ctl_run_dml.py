import os

from flask import Flask

import ctl_utils
from dml import dml_listener
from class_node import Net

if __name__ == '__main__':
	ip = '192.168.2.10'
	port = 9000
	net = Net (ip + ':' + str (port))
	dirname = os.path.abspath (os.path.dirname (__file__))

	cList = []
	start_id = 1
	cs1 = net.add_container_server ('se-lab-3700x', '192.168.2.5')
	for i in range (5):
		cList.append (net.add_container (cs1, 'n' + str (i + start_id), 'eth0', '/home/worker',
			['bash', 'run-dml.sh'], 'dml:v1.0', cpu=3, memory=9, unit='Gi'))
		cList [i + start_id - 1].add_envs ({'NAME': 'n' + str (i + start_id), 'PORT': str (8000 + i + start_id)})
		cList [i + start_id - 1].add_volume ('/home/lin/Desktop/net/worker', '/home/worker')
		cs1.add_port (cList [i + start_id - 1], 8000 + i + start_id, svc_node_port=30000 + i + start_id)

	start_id = 6
	cs2 = net.add_container_server ('se-lab-3990x', '192.168.2.8')
	for i in range (25):
		cList.append (net.add_container (cs2, 'n' + str (i + start_id), 'eth0', '/home/worker',
			['bash', 'run-dml.sh'], 'dml:v1.0', cpu=5, memory=9, unit='Gi'))
		cList [i + start_id - 1].add_envs ({'NAME': 'n' + str (i + start_id), 'PORT': str (8000 + i + start_id)})
		cList [i + start_id - 1].add_volume ('/home/lin/Desktop/net/worker', '/home/worker')
		cs2.add_port (cList [i + start_id - 1], 8000 + i + start_id, svc_node_port=30000 + i + start_id)

	net.save_node_ip (dirname)

	# for i in range (29):
	# 	for j in range (29 - i):
	# 		net.dual_link_limit (cList [i], cList [i + j + 1], bw=10, unit='mbps')
	# net.save_bw (dirname)

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
