import json
import os


def id_to_host (_id):
	if _id > 0:
		return 'n' + str (_id)
	return 'r' + str (-_id)


def read_json (filename):
	file_path = os.path.abspath (os.path.join (dirname, filename))
	with open (file_path, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


dirname = os.path.dirname (__file__)
env_addr_json = read_json ('env_addr.txt')
_device_number = env_addr_json ['device_number']
_container_number = env_addr_json ['container_number'] [-1]

env_train_json = read_json ('env_datasets.txt')
_batch_size = env_train_json ['batch_size']
_learning_rate = env_train_json ['learning_rate']
_start_index = env_train_json ['start_index']
_end_index = env_train_json ['end_index']

for i in range (_device_number + _container_number):
	_id = i - _device_number
	if _id >= 0:
		_id += 1
	_string = \
		'{\n' \
		+ '"learning_rate": ' + str (_learning_rate [i]) + ',\n' \
		+ '"batch_size": ' + str (_batch_size [i]) + ',\n' \
		+ '"start_index": ' + str (_start_index [i]) + ',\n' \
		+ '"end_index": ' + str (_end_index [i]) + '\n' \
		+ '}\n'
	env_path = os.path.abspath (os.path.join (dirname, '../env_datasets/', id_to_host (_id) + '.env'))
	with open (env_path, 'w') as file:
		file.writelines (_string)
