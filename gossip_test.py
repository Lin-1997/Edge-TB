import atexit
import time
from subprocess import Popen

import requests

worker_num = 2
iid_data_num = 100
fraction = 0.5
gpu_num = 2

each_worker_iid_data_num = int (iid_data_num / worker_num)
worker_num_per_gpu = worker_num / gpu_num


def create_node (index, client_num, start_data_index, end_data_index):
	gl_node_start_cmd = ["python", "gossip.py",
	                     "-i", str (index),
	                     "-n", str (client_num),
	                     "-j", str (start_data_index),
	                     "-k", str (end_data_index)]
	return Popen (gl_node_start_cmd)


def send_start_cmd (node_num):
	# 发送命令启动
	for node_index in range (node_num):
		requests.post ('http://localhost:' + str (9990 + node_index) + '/start_training')


def cleanup (all_processes):
	for p in all_processes:
		p.kill ()
	print ('Kill the processes of all nodes')


if __name__ == '__main__':
	processes = []
	for node_index in range (worker_num):
		# threading.Thread(target=create_node, args=(
		#    node_index, worker_num, node_index * each_worker_iid_data_num, (node_index + 1) * each_worker_iid_data_num
		# )).start()
		process = create_node (node_index, worker_num, node_index * each_worker_iid_data_num,
		                                               (node_index + 1) * each_worker_iid_data_num)
		processes.append (process)
	time.sleep (5)
	atexit.register (cleanup, processes)
	send_start_cmd (worker_num)
	print ("Run success.")
	processes [0].wait ()
