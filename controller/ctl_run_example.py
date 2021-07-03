import os

from flask import Flask

import ctl_utils
import fl_manager
from class_node import Net

# we made up the following physical hardware so this example is NOT runnable.
if __name__ == '__main__':
	# path of this file.
	dirname = os.path.abspath (os.path.dirname (__file__))
	# ip of this ctl.
	ip = '192.168.1.10'
	# port of this Flask emulator.
	port = 3333
	net = Net (ip, port)
	# declare a nfs read-only absolute path in this ctl.
	net.add_nfs (tag='dml_app', ip='192.168.1.0', mask=24,
		path=os.path.join (dirname, 'dml_app'))
	net.add_nfs (tag='dataset', ip='192.168.1.0', mask=24,
		path=os.path.join (dirname, 'dataset'))
	# restore nfs to system settings.
	ctl_utils.restore_nfs ()
	# export the path through nfs.
	ctl_utils.export_nfs (net)
	# Please note that the success of exporting the path also depends on
	# your firewall policy, the rwx mode of the path, etc.

	# in dml, the node name starts with a letter, followed by numbers, e.g., n1, n2, p1.
	# emulated nodes listen on port 4444, and map port 4444 to host port 8000+x,
	# where x is the numeric part of the name, e.g., n1 map port 4444 to host port 8001.
	# physical nodes listen on port 4444.
	# with these rules, we can use controller/dml_tool/*_structure_conf.py
	# to quickly generate the  ip:port part of conf files for each physical and emulated node.
	# we do not recommend changing this port number.
	dml_port = 4444

	# define your network >>>

	# store emulated nodes.
	nList = []

	# declare a Emulator, which should run the worker/agent.py in advance.
	emu1 = net.add_emulator (name='emulator-1', ip='192.168.1.11')

	# make the nfs shared path in this ctl available for emulated nodes in a emulator.
	# emulator's ip should in the subnet of ${ip/mask} defined in above add_nfs ().
	emu1.mount_nfs (tag='dml_app')
	emu1.mount_nfs ('dataset')
	# Please note that the success of mounting the path also depends on
	# your firewall policy, the rwx mode of the path, etc.

	# add a emulated node to a emulator, which will be done after you run this python code.
	# the total cpu and memory resources can not exceed the resources owned by the emulator.
	# the emulated node uses at most ${cpu} CPU cores (more accurately threads).
	# if the emulated node asks for more than ${memory unit} memory, it will be killed.
	nList.append (emu1.add_node (name='n1', nic='eth0', working_dir='/home/worker/dml_app',
		cmd=['python3', 'fl_aggregator.py'], image='dml:v1.0', cpu=4, memory=4, unit='G'))
	# ${host_path} can use absolute path starting from / or
	# relative path starting from the directory of the worker/.
	# ${node_path} can only use absolute path starting from /.
	nList [0].add_volume (host_path='/path/in/emulator-1/to/worker/dml_file',
		node_path='/home/worker/dml_file')
	# ${node_path} can only use absolute path starting from /.
	nList [0].add_nfs (tag='dml_app', node_path='/home/worker/dml_app')
	nList [0].add_nfs ('dataset', '/home/worker/dataset')
	nList [0].add_port (port=dml_port, host_port=8001)

	# add many emulated nodes.
	start_id = 2
	emu2 = net.add_emulator ('emulator-2', '192.168.1.12')
	emu2.mount_nfs ('dml_app')
	emu2.mount_nfs ('dataset')
	for i in range (3):
		nList.append (emu2.add_node ('n' + str (i + start_id), 'eth0', '/home/worker/dml_app',
			['python3', 'fl_trainer.py'], 'dml:v1.0', cpu=1, memory=2, unit='G'))
		# ${host_path} means /path/in/emulator-2/to/worker/dml_file in this example.
		nList [-1].add_volume ('./dml_file', '/home/worker/dml_file')
		nList [-1].add_nfs ('dml_app', '/home/worker/dml_app')
		nList [-1].add_nfs ('dataset', '/home/worker/dataset')
		nList [-1].add_port (dml_port, 8000 + i + start_id)

	# declare a physical node,
	# which should run the worker/agent.py in advance.
	p1 = net.add_physical_node (name='p1', nic='eth0', ip='192.168.1.13')
	# physical node's ip should in the subnet of ${ip/mask} defined in above add_nfs ().
	# ${mount_point} can use absolute path starting from / or
	# relative path starting from the directory of the worker/agent.py file.
	# ${mount_point} means /path/in/p1/to/worker/dml_app in this example.
	p1.mount_nfs (tag='dml_app', mount_point='./dml_app')
	p1.mount_nfs (tag='dataset', mount_point='./dataset')
	# set physical node's role.
	# ${working_dir} can use absolute path or relative path as above mount_nfs ().
	p1.set_cmd (working_dir='dml_app', cmd=['python3', 'fl_trainer.py'])

	# save the node's information as node_ip.json file.
	net.save_node_ip ()

	# add a link with limited bandwidth from one node to another,
	# or between two nodes through Linux Traffic Control.
	# net.asymmetrical_link (nList [0], nList [2], bw=500, unit='kbps')
	# net.symmetrical_link (p1, nList [1], bw=2, unit='mbps')

	# if you set the tc settings manually,
	# you can save them as a json file,
	# and load it by load_bw () in the next time.
	# net.save_bw ()

	# if you have a large number of densely connected nodes,
	# we recommend using load_bw ().
	# we cannot set the bandwidth between two nodes twice,
	# so we comment out the above asymmetrical_link () and symmetrical_link ().

	# load tc settings from links.json.
	links_json = ctl_utils.read_json (os.path.join (dirname, 'links.json'))
	net.load_bw (links_json)
	"""
	the contents in this example links.json are:
	
	{
	"p1":[{"dest":"n1","bw":"5mbps"},
		{"dest":"n3","bw":"3mbps"}],
	"n1":[{"dest":"p1","bw":"5mbps"},
		{"dest":"n2","bw":"3mbps"},
		{"dest":"n3","bw":"3mbps"},
		{"dest":"n4","bw":"3mbps"}],
	"n2":[{"dest":"n1","bw":"1mbps"},
		{"dest":"n4","bw":"3mbps"}],
	"n3":[{"dest":"n1","bw":"1mbps"}],
	"n4":[{"dest":"n1","bw":"1mbps"},
		{"dest":"p1","bw":"5mbps"}]
	}
	
	it takes a while to deploy the tc settings.
	when the terminal prints "tc finish", tc settings of all emulated and physical nodes are deployed.
	please make sure your node communicate with other nodes after "tc finish".
	"""

	# save the deployment of emulated nodes as ${emulator.name}.yml file.
	net.save_yml ()

	# <<< define your network

	app = Flask (__name__)

	# here we use POST at '/print'.
	ctl_utils.print_listener (app)

	# here we use POST at '/docker/tc'.
	ctl_utils.docker_tc_listener (app, net)
	# send ctl's ${ip:port} to the agent of emulators.
	ctl_utils.send_docker_address (net)
	# send the Dockerfile and dml_req.txt to the agent of emulators.
	# the path should be just a directory.
	# no need to call this function every time, unless you need to build a new docker image.
	path_dockerfile = os.path.join (dirname, 'dml_app/Dockerfile')
	path_req = os.path.join (dirname, 'dml_app/dml_req.txt')
	ctl_utils.deploy_dockerfile (net, 'dml:v1.0', path_dockerfile, path_req)

	# send the nfs settings to physical nodes.
	ctl_utils.send_device_nfs (net)
	# send the envs to physical nodes.
	# we have added some env by default, so you need to call this function
	# even if you don’t add custom env.
	ctl_utils.send_device_env (net)
	# send the dml_req.txt to physical nodes.
	# the path should be just a directory.
	# no need to call this function every time, unless you need to install some new packages.
	path_req = os.path.join (dirname, 'dml_app/dml_req.txt')
	ctl_utils.sent_device_req (net, path_req)

	if net.tcLinkNumber > 0:
		# send the tc settings to the agent of emulators.
		ctl_utils.send_docker_tc (net)
		# send the tc settings to physical nodes.
		ctl_utils.send_device_tc (net)
	else:
		print ('tc finish')

	# here we use GET at '/update/tc'
	ctl_utils.update_tc_listener (app, net)
	"""
	you can send a GET request to ctl's /update/tc at any time
	to update the tc settings of emulated and/or physical nodes. 

	for example, curl http://192.168.1.10:3333/update/tc?file=links2.json
	the contents in this example links2.json are:

	{
	"n1":[{"dest":"p1","bw":"3mbps"},
		{"dest":"n2","bw":"3mbps"},
		{"dest":"n3","bw":"3mbps"},
		{"dest":"n4","bw":"3mbps"}],
	"n4":[{"dest":"n1","bw":"2mbps"},
		{"dest":"p1","bw":"3mbps"}]
	}

	we will clear the tc settings of n1 and n4 and deploy the new one dynamically
	without stop nodes.
	for the above reasons, even if the bw from n1 to n2, n3 and n4 does not change,
	they need to be specified.
	"""

	# when you finish your experiments, you should restore your emulators and physical nodes.
	# first restore emulators, then restore physical nodes, and finally restore ctl's nfs.
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
	fl_manager.manager (app, net)

	# send the cmd to the agent of physical nodes.
	ctl_utils.deploy_all_device (net)
	# send the yml files to the agent of emulators.
	ctl_utils.deploy_all_yml (net)

	app.run (host='0.0.0.0', port=port, threaded=True)
