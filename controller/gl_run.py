import os

from base import default_testbed
from base.utils import read_json
from gl_manager import GlManager

# path of this file.
dirName = os.path.abspath (os.path.dirname (__file__))

# we made up the following physical hardware so this example is NOT runnable.
if __name__ == '__main__':
	testbed = default_testbed (ip='192.168.1.10', dir_name=dirName, manager_class=GlManager)

	# export a nfs read-only absolute path in this ctl so that
	# emulated nodes and physical nodes can mount it.
	# Please note that the success of exporting the path also depends on
	# your firewall policy, the rwx mode of the path, etc.
	nfsApp = testbed.add_nfs (tag='dml_app', path=os.path.join (dirName, 'dml_app'))
	nfsDataset = testbed.add_nfs (tag='dataset', path=os.path.join (dirName, 'dataset'))

	# define your network >>>

	# declare an emulator, which should run the worker/agent.py in advance.
	emu1 = testbed.add_emulator (name='emulator-1', ip='192.168.1.11', cpu=16, ram=64, unit='G')

	# add an emulated node to an emulator, which will be done after you run this python code.
	# the total cpu and memory resources can not exceed the resources owned by the emulator.
	# the emulated node uses at most ${cpu} CPU threads.
	# if the emulated node asks for more than ${memory unit} memory, it will be killed.
	en = testbed.add_emulated_node (name='n1', working_dir='/home/worker/dml_app',
		cmd=['python3', 'gl_peer.py'], image='dml:v1.0', cpu=4, ram=4, unit='G', emulator=emu1)
	# ${local_path} can use absolute path starting from / or
	# relative path starting from the directory of the worker/.
	# ${node_path} can only use absolute path starting from /.
	en.mount_local_path (local_path='/path/in/emulator-1/to/worker/dml_file',
		node_path='/home/worker/dml_file')
	# ${node_path} can only use absolute path starting from /.
	en.mount_nfs (nfs=nfsApp, node_path='/home/worker/dml_app')
	en.mount_nfs (nfsDataset, '/home/worker/dataset')

	# add many emulated nodes.
	emu2 = testbed.add_emulator ('emulator-2', '192.168.1.12', cpu=128, ram=256, unit='G')
	for i in range (2, 5):
		en = testbed.add_emulated_node ('n' + str (i), '/home/worker/dml_app',
			['python3', 'gl_peer.py'], 'dml:v1.0', cpu=1, ram=2, unit='G', emulator=emu2)
		# ${host_path} means /path/in/emulator-2/to/worker/dml_file in this example.
		en.mount_local_path ('./dml_file', '/home/worker/dml_file')
		en.mount_nfs (nfsApp, '/home/worker/dml_app')
		en.mount_nfs (nfsDataset, '/home/worker/dataset')

	# declare a physical node,
	# which should run the worker/agent.py in advance.
	p1 = testbed.add_physical_node (name='p1', nic='eth0', ip='192.168.1.13')
	# ${mount_point} can use absolute path starting from / or
	# relative path starting from the directory of the worker/agent.py file.
	# ${mount_point} means /path/in/p1/to/worker/dml_app in this example.
	p1.mount_nfs (nfs=nfsApp, mount_point='./dml_app')
	p1.mount_nfs (nfsDataset, './dataset')
	# set physical node's role.
	# ${working_dir} can use absolute path or relative path as above mount_nfs ().
	p1.set_cmd (working_dir='dml_app', cmd=['python3', 'gl_peer.py'])

	# load tc settings from links.json.
	links_json = read_json (os.path.join (dirName, 'links.json'))
	testbed.load_link (links_json)
	"""
	the contents in this example links.json are:

	{
	  "p1": [
	    {"dest": "n1", "bw": "5mbps"},
	    {"dest": "n4", "bw": "3mbps"}
	  ],
	  "n1": [
	    {"dest": "p1", "bw": "3mbps"},
	    {"dest": "n2", "bw": "3mbps"},
	    {"dest": "n3", "bw": "3mbps"},
	    {"dest": "n4", "bw": "3mbps"}
	  ],
	  "n2": [
	    {"dest": "n1", "bw": "1mbps"},
	    {"dest": "n3", "bw": "2mbps"},
	    {"dest": "n4", "bw": "3mbps"}
	  ],
	  "n3": [
	    {"dest": "n1", "bw": "4mbps"},
	    {"dest": "n2", "bw": "1mbps"}
	  ],
	  "n4": [
	    {"dest": "n1", "bw": "1mbps"},
	    {"dest": "n2", "bw": "5mbps"},
	    {"dest": "p1", "bw": "2mbps"}
	  ]
	}

	it takes a while to deploy the tc settings.
	when the terminal prints "tc finish", tc settings of all emulated and physical nodes are deployed.
	please make sure your node communicate with other nodes after "tc finish".

	you can send a GET request to ctl's /update/tc at any time
	to update the tc settings of emulated and/or physical nodes. 

	for example, curl http://192.168.1.10:3333/update/tc?file=links2.json
	the contents in this example links2.json are:

	{
	  "n1": [
	    {"dest": "p1", "bw": "1mbps"},
	    {"dest": "n2", "bw": "3mbps"},
	    {"dest": "n3", "bw": "3mbps"},
	    {"dest": "n4", "bw": "3mbps"}
	  ],
	  "n4": [
	    {"dest": "n1", "bw": "3mbps"},
	    {"dest": "n2", "bw": "5mbps"},
	    {"dest": "n3", "bw": "1mbps"},
	    {"dest": "p1", "bw": "2mbps"}
	  ]
	}

	we will clear the tc settings of n1 and n4 and deploy the new one dynamically
	without stop nodes.
	for the above reasons, even if the bw from n1 to n2, n3 and n4 does not change,
	they need to be specified.
	"""

	# <<< define your network

	# when you finish your experiments, you should restore your emulators and physical nodes.
	# GET at '/emulated/stop', '/emulated/clear' and '/emulated/reset',
	# GET at '/physical/stop', '/physical/clear/tc', '/physical/clear/nfs' and 'physical/reset',
	# these requests can be received by controller/base/manager.py, route_emulated_stop (), ect.
	testbed.start ()
