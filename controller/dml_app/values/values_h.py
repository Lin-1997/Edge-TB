import json
import os


def read_json (filename: str):
	with open (filename, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


def get_values (name):
	file_path = os.path.abspath (os.path.join (os.path.dirname (__file__),
		'../../dml_file/conf', name + '.conf'))
	values = read_json (file_path)

	if 'type' not in values:
		return values

	values ['current_round'] = [0] * len (values ['layer'])
	values ['received_number'] = [0] * len (values ['layer'])
	values ['received_weights'] = [[] for _ in range (len (values ['layer']))]

	return values
