import json
from typing import Dict, IO

import requests


def read_json (path: str):
	with open (path, 'r') as f:
		return json.loads (f.read ().replace ('\'', '\"'))


def send_data (method: str, path: str, address: str, port: int = None,
		data: Dict [str, str] = None, files: Dict [str, IO] = None) -> str:
	"""
	send a request to http://${address/path} or http://${ip:port/path}.
	@param method: 'GET' or 'POST'.
	@param path:
	@param address: ip:port if ${port} is None else only ip.
	@param port: only used when ${address} is only ip.
	@param data: only used in 'POST'.
	@param files: only used in 'POST'.
	@return: response.text
	"""
	if port:
		address += ':' + str (port)
	if method.upper () == 'GET':
		res = requests.get ('http://' + address + '/' + path)
		return res.text
	elif method.upper () == 'POST':
		res = requests.post ('http://' + address + '/' + path, data=data, files=files)
		return res.text
	else:
		return 'err method ' + method
