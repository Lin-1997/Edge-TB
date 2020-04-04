import os
import threading

client_num = 4
iid_data_num = 100
gpu_num = 2

each_client_iid_data_num = int(iid_data_num / client_num)
client_num_per_gpu = client_num / gpu_num

def create_client(gpu_index, num, index, start_data_idnex, end_data_index):
	os.system("CUDA_VISIBLE_DEVICES=" + str(gpu_index) + " python client.py -n " + str(num) + " -i " + str(index) + " --start_data_index=" + str(start_data_idnex) + " --end_data_index=" + str(end_data_index))

def create_command_server(client_num):
	os.system("python command_server.py -n " + str(client_num))

for client_index in range(client_num):
	# threading.Thread(target=create_client, args=(int(client_index / client_num_per_gpu), client_num, client_index, client_index * each_client_iid_data_num, (client_index + 1) * each_client_iid_data_num)).start()
	threading.Thread(target=create_client, args=(
		1, client_num, client_index, client_index * each_client_iid_data_num,
		(client_index + 1) * each_client_iid_data_num)).start()
threading.Thread(target=create_command_server, args=(client_num,)).start()