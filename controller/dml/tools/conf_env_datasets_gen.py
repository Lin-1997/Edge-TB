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


if __name__ == '__main__':
	dirname = os.path.dirname (__file__)
	env_addr_json = read_json ('env_addr.txt')
	_device_number = env_addr_json ['device_number']
	_container_number = env_addr_json ['container_number'] [-1]

	env_datasets_json = read_json ('env_datasets.txt')
	_batch_size = env_datasets_json ['batch_size']
	_train_start_i = env_datasets_json ['train_start_i']
	_train_len = env_datasets_json ['train_len']
	_test_start_i = env_datasets_json ['test_start_i']
	_test_len = env_datasets_json ['test_len']

	for i in range (_device_number + _container_number):
		_id = i - _device_number
		if _id >= 0:
			_id += 1
		_string = \
			'{\n' \
			+ '"batch_size": ' + str (_batch_size [i]) + ',\n' \
			+ '"train_start_i": ' + str (_train_start_i [i]) + ',\n' \
			+ '"train_len": ' + str (_train_len [i]) + ',\n' \
			+ '"test_start_i": ' + str (_test_start_i [i]) + ',\n' \
			+ '"test_len": ' + str (_test_len [i]) + '\n' \
			+ '}\n'
		env_path = os.path.abspath (os.path.join (dirname, '../env_datasets/', id_to_host (_id) + '.env'))
		with open (env_path, 'w') as file:
			file.writelines (_string)
