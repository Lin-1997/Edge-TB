import argparse
import json
import os


def read_json (filename):
	with open (os.path.join (dirname, filename), 'r') as f:
		return json.loads (f.read ().replace ('\'', '\"'))


if __name__ == '__main__':
	dirname = os.path.abspath (os.path.dirname (__file__))
	parser = argparse.ArgumentParser ()
	parser.add_argument ('-f', '--file', dest='file', required=True, type=str,
		help='./relative/path/to/conf/file')
	args = parser.parse_args ()

	conf_json = read_json (args.file)
	for node_name in conf_json:
		node_conf = conf_json [node_name]
		if 'test_len' not in node_conf:
			node_conf ['test_len'] = -1
			node_conf ['test_start_index'] = -1
		if 'train_len' not in node_conf:
			node_conf ['train_len'] = -1
			node_conf ['train_start_index'] = -1

		conf_path = os.path.join (dirname, '../dml_file/conf', node_name + '_dataset.conf')
		with open (conf_path, 'w') as f:
			f.writelines (json.dumps (node_conf, indent=2))
