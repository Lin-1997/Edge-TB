import os

from worker_utils import read_json


def get_values (name):
	file_path = os.path.abspath (os.path.join (os.path.dirname (__file__),
		'../env/', name + '.env'))
	values = read_json (file_path)

	if 'type' not in values:
		return values

	values ['current_round'] = [0] * values ['layer_count']
	values ['received_count'] = [0] * values ['layer_count']
	values ['received_weights'] = [[] for _ in range (values ['layer_count'])]

	return values
