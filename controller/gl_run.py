import os
import random

from flask import Flask

import ctl_utils
import gl_manager
from class_node import Net

if __name__ == '__main__':
	dirname = os.path.abspath (os.path.dirname (__file__))
	ip = '192.168.2.31'
	port = 3333
	net = Net (ip, port)
	net.add_nfs (tag='dml_app', ip='192.168.2.0', mask=24,
		path=os.path.join (dirname, 'dml_app'))
	net.add_nfs (tag='dataset', ip='192.168.2.0', mask=24,
		path=os.path.join (dirname, 'dataset'))
	ctl_utils.restore_nfs ()
	ctl_utils.export_nfs (net)

	dml_port = 4444

	nList = []
	nDict = {}

	nList.append (net.add_physical_node (name='p1', nic='eth0', ip='192.168.2.23'))
	nDict ['p1'] = []
	nList [-1].mount_nfs (tag='dml_app', mount_point='./dml_app')
	nList [-1].mount_nfs (tag='dataset', mount_point='./dataset')
	nList [-1].set_cmd (working_dir='dml_app', cmd=['python3', 'gl_peer.py'])

	nList.append (net.add_physical_node (name='p2', nic='eth0', ip='192.168.2.24'))
	nDict ['p2'] = []
	nList [-1].mount_nfs (tag='dml_app', mount_point='./dml_app')
	nList [-1].mount_nfs (tag='dataset', mount_point='./dataset')
	nList [-1].set_cmd (working_dir='dml_app', cmd=['python3', 'gl_peer.py'])

	nList.append (net.add_physical_node (name='p3', nic='eth0', ip='192.168.2.27'))
	nDict ['p3'] = []
	nList [-1].mount_nfs (tag='dml_app', mount_point='./dml_app')
	nList [-1].mount_nfs (tag='dataset', mount_point='./dataset')
	nList [-1].set_cmd (working_dir='dml_app', cmd=['python3', 'gl_peer.py'])

	start_index = 1
	emu1 = net.add_emulator ('3700x', '192.168.2.5')
	emu1.mount_nfs ('dml_app')
	emu1.mount_nfs ('dataset')
	for i in range (16):
		nList.append (emu1.add_node ('n' + str (i + start_index), 'eth0', '/home/worker/dml_app',
			['python3', 'gl_peer.py'], 'dml:v1.0', cpu=1, memory=1, unit='G'))
		nDict ['n' + str (i + start_index)] = []
		nList [-1].add_volume ('./dml_file', '/home/worker/dml_file')
		nList [-1].add_nfs ('dml_app', '/home/worker/dml_app')
		nList [-1].add_nfs ('dataset', '/home/worker/dataset')
		nList [-1].add_port (dml_port, 8000 + i + start_index)

	start_index = 17
	emu2 = net.add_emulator ('3990x', '192.168.2.10')
	emu2.mount_nfs ('dml_app')
	emu2.mount_nfs ('dataset')
	for i in range (128):
		nList.append (emu2.add_node ('n' + str (i + start_index), 'eth0', '/home/worker/dml_app',
			['python3', 'gl_peer.py'], 'dml:v1.0', cpu=1, memory=1, unit='G'))
		nDict ['n' + str (i + start_index)] = []
		nList [-1].add_volume ('./dml_file', '/home/worker/dml_file')
		nList [-1].add_nfs ('dml_app', '/home/worker/dml_app')
		nList [-1].add_nfs ('dataset', '/home/worker/dataset')
		nList [-1].add_port (dml_port, 8000 + i + start_index)

	net.save_node_ip ()

	for i in range (147):
		for j in range (10):
			name = nList [i].name
			index = random.randint (0, 146)
			if index != i and index not in nDict [name]:
				net.symmetrical_link (nList [i], nList [index], bw=random.randint (200, 500), unit='kbps')
				nDict [name].append (index)
				nDict [nList [index].name].append (i)

	net.save_bw ()

	# links_json = ctl_utils.read_json (os.path.join (dirname, 'links.json'))
	# net.load_bw (links_json)

	net.save_yml ()

	app = Flask (__name__)

	ctl_utils.print_listener (app)

	ctl_utils.docker_tc_listener (app, net)
	ctl_utils.send_docker_address (net)
	# path_dockerfile = os.path.join (dirname, 'dml_app/Dockerfile')
	# path_req = os.path.join (dirname, 'dml_app/dml_req.txt')
	# ctl_utils.deploy_dockerfile (net, 'dml:v1.0', path_dockerfile, path_req)

	ctl_utils.send_device_nfs (net)
	ctl_utils.send_device_env (net)
	# path_req = os.path.join (dirname, 'dml_app/dml_req.txt')
	# ctl_utils.sent_device_req (net, path_req)

	if net.tcLinkNumber > 0:
		ctl_utils.send_docker_tc (net)
		ctl_utils.send_device_tc (net)
	else:
		print ('tc finish')

	ctl_utils.update_tc_listener (app, net)

	ctl_utils.docker_controller_listener (app, net)
	ctl_utils.device_controller_listener (app, net)
	ctl_utils.clear_nfs_listener (app)

	gl_manager.manager (app, net)

	ctl_utils.deploy_all_device (net)
	ctl_utils.deploy_all_yml (net)

	app.run (host='0.0.0.0', port=port, threaded=True)
