"""
this file can generate a bw.txt suitable for class_node.py, Net.load_bw ().
you should provide the order of your nodes, the connection probability between nodes,
the maximum bw, the minimum bw and their unit.
we will ensure that the output is a connected graph,
so the proportion of nodes connected may be higher than the connection probability.
"""
import json
import os
import random

import numpy as np


def random_bw ():
	for i in range (node_number):
		for j in range (i, node_number):
			if i == j:
				bw_array [i] [j] = float ('inf')
			elif random.random () <= connection_probability:
				bw_array [i] [j] = random.uniform (min_bw, max_bw)
				if symmetry:
					bw_array [j] [i] = bw_array [i] [j]
				else:
					bw_array [j] [i] = random.uniform (min_bw, max_bw)


def dfs (i_node=0):
	v [i_node] = 1
	for i_next in range (node_number):
		if v [i_next] == 0 and bw_array [i_node] [i_next] > 0:
			dfs (i_next)


def no_connected ():
	for val in range (len (v)):
		if v [val] == 0:
			return val
	return 0


def ensure_connected ():
	start = no_connected ()
	while start != 0:
		# connected graph.
		v_temp = []
		for i in range (node_number):
			if v [i] == 1:
				v_temp.append (i)
		# randomly connect to a node in the connected graph.
		random.shuffle (v_temp)
		for j in v_temp:
			if v [j] == 1 and bw_array [start] [j] == 0:
				bw_array [start] [j] = random.uniform (min_bw, max_bw)
				if symmetry:
					bw_array [j] [start] = bw_array [start] [j]
				else:
					bw_array [j] [start] = random.uniform (min_bw, max_bw)
				break
		dfs (start)
		start = no_connected ()


def unit_degrade ():
	if unit in ['gbit', 'gbps']:
		return 'm' + unit [1:]
	elif unit in ['mbit', 'mbps']:
		return 'k' + unit [1:]
	else:
		return unit


def assign_unit ():
	for i in range (node_number):
		bw.append ([])
		for j in range (node_number):
			if i == j:
				bw [-1].append ('inf')
			elif bw_array [i] [j] == 0:
				bw [-1].append ('None')
			# no need or can't be downgraded.
			elif bw_array [i] [j] >= 50 or unit [0] == 'k':
				bw [-1].append (str (int (bw_array [i] [j])) + unit)
			# it better to be downgraded.
			else:
				bw [-1].append (str (int (bw_array [i] [j] * 1024)) + unit_d)


if __name__ == '__main__':
	# all configurable parameters.
	order = ['n1', 'n2', 'n3', 'n4', 'd1']
	connection_probability = 0.2
	min_bw = 2
	max_bw = 5
	unit = 'mbps'
	# if True, the bw from n1 to n2 will be the same as that from n2 to n1.
	# if False, they may have different values.
	symmetry = False
	# all configurable parameters.

	assert unit in ['kbit', 'mbit', 'gbit', 'kbps', 'mbps', 'gbps'], Exception (
		unit + ' is not in ["kbit", "mbit", "gbit", "kbps", "mbps", "gbps"]')

	unit_d = unit_degrade ()
	node_number = len (order)
	# bw array without unit.
	bw_array = np.zeros ((node_number, node_number))
	# whether nodes are connected.
	v = [0 for _ in range (node_number)]
	# randomly assign bw between nodes.
	random_bw ()

	# check whether it is a connected graph.
	dfs ()
	# make it a connected graph.
	ensure_connected ()
	# bw array with unit.
	bw = []
	assign_unit ()

	print (order)
	for line in bw:
		print (line)
	filename = os.path.abspath (os.path.join (os.path.dirname (__file__), '../bw.txt'))
	data = {'order': order, 'bw': bw}
	with open (filename, 'w')as f:
		f.writelines (json.dumps (data).replace ('], ', '],\n'))
