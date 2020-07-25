import json
import os


def read_env ():
	file_name = os.getenv ('HOSTNAME') + '.env'
	file_path = os.path.abspath (os.path.join (os.path.dirname (__file__), './env', file_name))
	file = open (file_path)
	env = json.loads (file.read ().replace ('\n', '').replace ('\r', '').replace ('\'', '\"'))
	file.close ()
	return env


def get_values ():
	return values


values = read_env ()
# 从MB/s变成B/s
for key in values ['switch'].keys ():
	values ['switch'] [key] = 1024 * 1024 * values ['switch'] [key]
for key in values ['node'].keys ():
	values ['node'] [key] = 1024 * 1024 * values ['node'] [key]