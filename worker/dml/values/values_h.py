import json
import os


def read_env (name):
	file_path = os.path.abspath (os.path.join (os.path.dirname (__file__), '../env/', name + '.env'))
	with open (file_path, 'r') as f:
		return json.loads (f.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))


def get_values (name):
	values = read_env (name)

	if 'type' not in values:
		return values

	values ['current_round'] = [0] * values ['layer_count']
	values ['received_count'] = [0] * values ['layer_count']
	values ['received_weights'] = [[] for _ in range (values ['layer_count'])]

	return values
