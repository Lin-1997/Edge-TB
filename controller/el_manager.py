import json
import os

import matplotlib.pyplot as plt
from flask import request

from base import Manager, Testbed
from base.utils import send_data


class ElManager (Manager):
	def __init__ (self, testbed: Testbed):
		super ().__init__ (testbed)
		self.perf = {}

		# collect the time required for 1 epoch training for each trainer in 1 layer.
		# they may help you decide how often trainers upload weights in el.
		@self.testbed.flask.route ('/perf', methods=['GET'])
		def route_perf ():
			node = request.args.get ('node')
			total_time = request.args.get ('time', type=float)
			print (node + ' use ' + str (total_time))
			with self.lock:
				self.perf [node] = total_time
				if len (self.perf) == self.nodeNumber:
					self.perf ['size'] = request.args.get ('size', type=float)
					file_path = os.path.join (self.testbed.dirName, 'dml_tool/perf.txt')
					with open (file_path, 'w') as f:
						f.write (json.dumps (self.perf))
					print ('performance collection completed, saved on ' + file_path)
			return ''

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
		Aggregate: accuracy=0.8999999761581421, round=1, layer=2,
		Train: loss=0.2740592360496521, round=1,
		we left a comma at the end for easy positioning and extending.
		"""
		acc_str = 'accuracy='
		layer_str = 'layer='
		loss_str = 'loss='
		acc_map = {}
		loss_list = []
		with open (os.path.join (self.logFileFolder, filename), 'r') as f:
			for line in f:
				if line.find ('Aggregate') != -1:
					acc_start_i = line.find (acc_str) + len (acc_str)
					acc_end_i = line.find (',', acc_start_i)
					acc = float (line [acc_start_i:acc_end_i])
					layer_start_i = line.find (layer_str) + len (layer_str)
					layer_end_i = line.find (',', layer_start_i)
					layer = int (line [layer_start_i:layer_end_i])
					acc_map.setdefault (layer, []).append (acc)
				elif line.find ('Train') != -1:
					loss_start_i = line.find (loss_str) + len (loss_str)
					loss_end_i = line.find (',', loss_start_i)
					loss = float (line [loss_start_i:loss_end_i])
					loss_list.append (loss)
		name = filename [:filename.find ('.log')]
		for layer in acc_map:
			plt.plot (acc_map [layer], 'go')
			plt.plot (acc_map [layer], 'r')
			plt.xlabel ('round')
			plt.ylabel ('accuracy')
			plt.ylim (0, 1)
			plt.title ('Accuracy')
			if layer == -1:
				plt.savefig (os.path.join (self.logFileFolder, 'png/', name + '-acc.png'))
			else:
				plt.savefig (os.path.join (self.logFileFolder, 'png/', name + '-L' + str (layer) + '-acc.png'))
			plt.cla ()
		if len (loss_list) != 0:
			plt.plot (loss_list, 'go')
			plt.plot (loss_list, 'r')
			plt.xlabel ('round')
			plt.ylabel ('loss')
			plt.ylim (0, loss_list [0] * 1.2)
			plt.title ('Loss')
			plt.savefig (os.path.join (self.logFileFolder, 'png/', name + '-loss.png'))
			plt.cla ()
