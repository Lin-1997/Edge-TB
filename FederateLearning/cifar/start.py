import os
import threading

client_num = 2
iid_data_num = 100
fraction_ratio = 0.5
gpu_num = 2

each_client_iid_data_num = int(iid_data_num / client_num)
client_num_per_gpu = client_num / gpu_num

def create_client(gpu_index, index, start_data_idnex, end_data_index):
    os.system("CUDA_VISIBLE_DEVICES=" + str(gpu_index) + " python client.py -i " + str(index) + " --start_data_index=" + str(start_data_idnex) + " --end_data_index=" + str(end_data_index))

def create_parameter_server(client_num, fraction_ratio):
    os.system("CUDA_VISIBLE_DEVICES=1 python parameter_server.py -n " + str(client_num) + " -c " + str(fraction_ratio))

for client_index in range(client_num):
    threading.Thread(target=create_client, args=(int(client_index / client_num_per_gpu), client_index, client_index * each_client_iid_data_num, (client_index + 1) * each_client_iid_data_num)).start()
threading.Thread(target=create_parameter_server, args=(client_num, fraction_ratio)).start()