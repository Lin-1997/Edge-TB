import os
import random

from flask import Flask

import ctl_utils
import el_manager
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

	start_id = 1
	emu1 = net.add_emulator ('3700x', '192.168.2.5')
	emu1.mount_nfs ('dml_app')
	emu1.mount_nfs ('dataset')
	for i in range (5):
		cpu = (i % 4) * 2
		if cpu == 0:
			cpu = 1
		nList.append (emu1.add_node ('n' + str (i + start_id), 'eth0', '/home/worker/dml_app',
			['python3', 'el_peer.py'], 'dml:v1.0', cpu=cpu, memory=5, unit='G'))
		nList [-1].add_volume ('./dml_file', '/home/worker/dml_file')
		nList [-1].add_nfs ('dml_app', '/home/worker/dml_app')
		nList [-1].add_nfs ('dataset', '/home/worker/dataset')
		nList [-1].add_port (dml_port, 8000 + i + start_id)

	start_id = 6
	emu2 = net.add_emulator ('3990x', '192.168.2.10')
	emu2.mount_nfs ('dml_app')
	emu2.mount_nfs ('dataset')
	for i in range (32):
		cpu = (i % 4) * 2
		if cpu == 0:
			cpu = 1
		nList.append (emu2.add_node ('n' + str (i + start_id), 'eth0', '/home/worker/dml_app',
			['python3', 'el_peer.py'], 'dml:v1.0', cpu=cpu, memory=5, unit='G'))
		nList [-1].add_volume ('./dml_file', '/home/worker/dml_file')
		nList [-1].add_nfs ('dml_app', '/home/worker/dml_app')
		nList [-1].add_nfs ('dataset', '/home/worker/dataset')
		nList [-1].add_port (dml_port, 8000 + i + start_id)

	p1 = net.add_physical_node (name='p1', nic='eth0', ip='192.168.2.23')
	p1.mount_nfs (tag='dml_app', mount_point='./dml_app')
	p1.mount_nfs (tag='dataset', mount_point='./dataset')
	p1.set_cmd (working_dir='dml_app', cmd=['python3', 'el_peer.py'])

	p2 = net.add_physical_node (name='p2', nic='eth0', ip='192.168.2.24')
	p2.mount_nfs (tag='dml_app', mount_point='./dml_app')
	p2.mount_nfs (tag='dataset', mount_point='./dataset')
	p2.set_cmd (working_dir='dml_app', cmd=['python3', 'el_peer.py'])
	net.symmetrical_link (p2, p1, bw=random.randint (200, 500), unit='kbps')

	p3 = net.add_physical_node (name='p3', nic='eth0', ip='192.168.2.27')
	p3.mount_nfs (tag='dml_app', mount_point='./dml_app')
	p3.mount_nfs (tag='dataset', mount_point='./dataset')
	p3.set_cmd (working_dir='dml_app', cmd=['python3', 'el_peer.py'])
	net.symmetrical_link (p3, p1, bw=random.randint (200, 500), unit='kbps')
	net.symmetrical_link (p3, p2, bw=random.randint (200, 500), unit='kbps')

	net.save_node_ip ()

	for i in range (len (nList) - 1):
		net.symmetrical_link (nList [i], p1, bw=random.randint (200, 500), unit='kbps')
		net.symmetrical_link (nList [i], p2, bw=random.randint (200, 500), unit='kbps')
		net.symmetrical_link (nList [i], p3, bw=random.randint (200, 500), unit='kbps')
		for j in range (i + 1, len (nList)):
			net.symmetrical_link (nList [i], nList [j], bw=random.randint (200, 500), unit='kbps')

	net.symmetrical_link (nList [-1], p1, bw=random.randint (200, 500), unit='kbps')
	net.symmetrical_link (nList [-1], p2, bw=random.randint (200, 500), unit='kbps')
	net.symmetrical_link (nList [-1], p3, bw=random.randint (200, 500), unit='kbps')

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

	el_manager.manager (app, net)

	ctl_utils.deploy_all_device (net)
	ctl_utils.deploy_all_yml (net)

	app.run (host='0.0.0.0', port=port, threaded=True)
