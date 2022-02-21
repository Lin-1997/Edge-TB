import os
from typing import Set

import matplotlib.pyplot as plt
from flask import request

from base import Manager, Testbed
from base.utils import send_data


class RaManager (Manager):
	def __init__ (self, testbed: Testbed):
		super ().__init__ (testbed)
		self.currentStage: str = 'train'
		self.currentStep: int = 0
		self.okNodes: Set = set ()
		self.finishedNodes: Set = set ()

		@self.testbed.flask.route ('/ok', methods=['POST'])
		def route_ok ():
			name = request.args.get ('name')
			self.testbed.executor.submit (self.on_route_ok, name)
			return ''

	def on_route_ok (self, name: str):
		with self.lock:
			self.okNodes.add (name)
			if len (self.okNodes) == self.nodeNumber:
				print ('stage finished by all nodes: ' + self.currentStage + ' ' + str (self.currentStep))
				self.okNodes.clear ()

				if self.currentStage == 'train':
					self.currentStage = 'reduce'
					self.currentStep = 1
				elif self.currentStage == 'reduce':
					if self.currentStep == self.nodeNumber - 1:
						self.currentStage = 'gather'
						self.currentStep = 1
					else:
						self.currentStep += 1
				elif self.currentStage == 'gather':
					if self.currentStep == self.nodeNumber - 1:
						self.currentStage = 'train'
						self.currentStep = 0
					else:
						self.currentStep += 1

				# send the command
				if self.currentStage == 'train':
					path = '/train'
				else:
					path = '/send?stage=' + self.currentStage + '&step=' + str (self.currentStep)

				for pn in self.pNode.values ():
					send_data ('GET', path, pn.ip, pn.port)
				for en in self.eNode.values ():
					send_data ('GET', path, en.ip, en.port)

	def on_route_start (self, req: request) -> str:
		for pn in self.pNode.values ():
			send_data ('GET', '/start', pn.ip, pn.port)
		for en in self.eNode.values ():
			send_data ('GET', '/start', en.ip, en.port)
		print ('start training')
		return ''

	def on_route_finish (self, req: request) -> bool:
		name = req.args.get ('name')
		print (name + ' is finished')
		with self.lock:
			self.finishedNodes.add (name)
			number = len (self.finishedNodes)
		return number == self.nodeNumber

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
