import os
import threading

# worker_num = 50
worker_num = 2
iid_data_num = 100
fraction = 0.5
gpu_num = 2

each_worker_iid_data_num = int (iid_data_num / worker_num)
worker_num_per_gpu = worker_num / gpu_num


def create_worker (gpu_index, index, start_data_index, end_data_index):
	# os.system("CUDA_VISIBLE_DEVICES=" + str(gpu_index) + " python w.py -i " + str(index) + " --start_data_index=" + str(start_data_idnex) + " --end_data_index=" + str(end_data_index))
	os.system ("python w.py -i " + str (index) + " --start_data_index=" + str (
		start_data_index) + " --end_data_index=" + str (end_data_index))


def create_parameter_server (worker_num, fraction):
	# os.system ("CUDA_VISIBLE_DEVICES=0 python a.py -n " + str (worker_num) + " -f " + str (fraction))
	os.system ("python a.py -n " + str (worker_num) + " -f " + str (fraction))


for worker_index in range (worker_num):
	threading.Thread (target=create_worker, args=(
		int (worker_index / worker_num_per_gpu), worker_index, worker_index * each_worker_iid_data_num,
		(worker_index + 1) * each_worker_iid_data_num)).start ()
threading.Thread (target=create_parameter_server, args=(worker_num, fraction)).start ()
