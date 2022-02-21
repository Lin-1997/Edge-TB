import os

import matplotlib.pyplot as plt
from flask import request

from base import Manager, Testbed
from base.utils import send_data


class FlManager (Manager):
	def __init__ (self, testbed: Testbed):
		super ().__init__ (testbed)

	def on_route_start (self, req: request) -> str:
		root = req.args.get ('root', type=str, default='')
		if root == '':
			return 'name cannot be empty'
		if root in self.pNode:
			send_data ('GET', '/start', self.pNode [root].ip, self.pNode [root].port)
		elif root in self.eNode:
			send_data ('GET', '/start', self.eNode [root].ip, self.eNode [root].port)
		else:
			return 'no such node called ' + root
		print ('start training')
		return ''

	def on_route_finish (self, req: request) -> bool:
		"""
		only the root node will send message to here.
		"""
		return True

	def parse_log_file (self, req: request, filename: str):
		"""
		parse log files into pictures.
		the log files format comes from worker/worker_utils.py, log_acc () and log_loss ().
		Aggregate: accuracy=0.8999999761581421, round=1,
		Train: loss=0.2740592360496521, round=1,
		we left a comma at the end for easy positioning and extending.
		"""
		acc_str = 'accuracy='
		loss_str = 'loss='
		acc_list = []
		loss_list = []
		with open (os.path.join (self.logFileFolder, filename), 'r') as f:
			for line in f:
				if line.find ('Aggregate') != -1:
					acc_start_i = line.find (acc_str) + len (acc_str)
					acc_end_i = line.find (',', acc_start_i)
					acc = float (line [acc_start_i:acc_end_i])
					acc_list.append (acc)
				elif line.find ('Train') != -1:
					loss_start_i = line.find (loss_str) + len (loss_str)
					loss_end_i = line.find (',', loss_start_i)
					loss = float (line [loss_start_i:loss_end_i])
					loss_list.append (loss)
		name = filename [:filename.find ('.log')]
		if acc_list:
			plt.plot (acc_list, 'go')
			plt.plot (acc_list, 'r')
			plt.xlabel ('round')
			plt.ylabel ('accuracy')
			plt.ylim (0, 1)
			plt.title ('Accuracy')
			plt.savefig (os.path.join (self.logFileFolder, 'png/', name + '-acc.png'))
			plt.cla ()
		if loss_list:
			plt.plot (loss_list, 'go')
			plt.plot (loss_list, 'r')
			plt.xlabel ('round')
			plt.ylabel ('loss')
			plt.ylim (0, loss_list [0] * 1.2)
			plt.title ('Loss')
			plt.savefig (os.path.join (self.logFileFolder, 'png/', name + '-loss.png'))
			plt.cla ()
