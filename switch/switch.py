import io
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from flask import Flask, request

import values_s

v = values_s.get_values ()
app = Flask (__name__)
executor = ThreadPoolExecutor (1)


def simulate_sleep (size, s_time, bw):
	n_time = float (format (size / bw, '.1f'))
	c_time = time.time ()
	t = s_time + n_time - c_time
	if t > 0.2:
		print ("sleep " + str (t))
		time.sleep (t)


@app.route ('/hi', methods=['GET'])
def route_hi ():
	return 'Switch ' + os.getenv ('HOSTNAME') + ' in ' + str (os.getenv ('PORT')) + '\r\n'


@app.route ('/forward', methods=['POST'])
def route_forward ():
	weights = request.files.get ('weights')
	data = {'host': request.form ['host'],
	        'path': request.form ['path'],
	        'layer': request.form.get ('layer', type=int)}
	s_time = request.args.get ('time', type=float)
	bw = request.args.get ('bw', type=float)

	temp_file = io.BytesIO ()
	weights.save (temp_file)
	weights.seek (0)
	size = len (weights.read ())  # 模拟网络传输时延
	temp_file.seek (0)

	executor.submit (on_route_forward, temp_file, data, size, s_time, bw)
	return ''


def on_route_forward (temp_file, data, size, _time, bw):
	simulate_sleep (size, _time, bw)
	file = {'weights': temp_file}
	s_time = format (time.time (), '.1f')
	addr = v ['forward'] [data ['host']]

	if addr in v ['node']:
		path = addr + data ['path'] + '?layer=' + str (data ['layer']) \
		       + '&time=' + str (s_time) + '&bw=' + str (v ['node'] [addr])
		requests.post (path, files=file)
	else:
		path = addr + '/forward?time=' + str (s_time) + '&bw=' \
		       + str (v ['switch'] [addr])
		requests.post (path, data=data, files=file)


app.run (host='0.0.0.0', port=os.getenv ('PORT'), threaded=True)
