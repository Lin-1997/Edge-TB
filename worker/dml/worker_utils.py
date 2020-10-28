"""
copy this file into your project, if it is useful :-)
"""
import os

import requests

net_ctl_address = os.getenv ('NET_CTL_ADDRESS')


def send_print (msg):
	requests.post ('http://' + net_ctl_address + '/print', data={'msg': msg})
