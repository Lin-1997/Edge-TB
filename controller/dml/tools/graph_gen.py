import math
import os
import random

import numpy as np
from numpy.linalg import solve


def graph_random ():
	for i in range (node_number):
		for j in range (i, node_number):
			if i == j:
				g [i] [j] = float ('inf')
			elif random.random () <= connection_probability:
				g [i] [j] = round (random.uniform (min_bw, max_bw), 2)
				g [j] [i] = g [i] [j]


def graph_2d ():
	global max_dist, min_dist
	for i in range (node_number):
		g [i] [i] = float ('inf')
		x1 = round (random.uniform (0, L), 1)
		y1 = round (random.uniform (0, L), 1)
		X_list [i] = x1
		Y_list [i] = y1
		for j in range (i):
			x2 = X_list [j]
			y2 = Y_list [j]
			if x1 - connection_distance <= x2 <= x1 + connection_distance and y1 - connection_distance <= y2 <= y2 + connection_distance:
				dist = round (((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5, 4)
				if dist > max_dist:
					max_dist = dist
				if dist < min_dist:
					min_dist = dist
				g [i] [j] = dist
				g [j] [i] = g [i] [j]


def dfs (i_node=0):
	v [i_node] = 1
	for i_next in range (node_number):
		if v [i_next] == 0 and g [i_node] [i_next] > 0:
			dfs (i_next)


def no_conn ():
	for val in range (len (v)):
		if v [val] == 0:
			return val
	return 0


def ensure_conn ():
	global max_dist, min_dist
	start = no_conn ()
	while start != 0:
		v_temp = []
		for i in range (node_number):
			if v [i] == 1:
				v_temp.append (i)
		random.shuffle (v_temp)
		for j in v_temp:
			if v [j] == 1 and g [start] [j] == 0:
				dist = round (((X_list [start] - X_list [j]) ** 2 + (Y_list [start] - Y_list [j]) ** 2) ** 0.5, 4)
				g [start] [j] = dist
				g [j] [start] = g [start] [j]
				if dist > max_dist:
					max_dist = dist
				if dist < min_dist:
					min_dist = dist
				v [start] = 1
				break
		dfs (start)
		start = no_conn ()


def calculate_equation ():
	global a, b, c
	cal1 = np.mat ([[min_dist ** 2, min_dist, 1], [(min_dist + max_dist) ** 2 / 16, (min_dist + max_dist) / 4, 1],
	                [max_dist ** 2, max_dist, 1]])
	cal2 = np.mat ([0, (max_bw - min_bw) / 3, max_bw - min_bw]).T
	result = solve (cal1, cal2).tolist ()
	a = round (result [0] [0], 4)
	b = round (result [1] [0], 4)
	c = round (result [2] [0], 4)


def assign_bw ():
	for i in range (node_number):
		for j in range (i):
			if i == j:
				continue
			elif g [i] [j] != 0.0:
				g [i] [j] = max (min_bw, round (max_bw - a * g [i] [j] ** 2 - b * g [i] [j] - c, 4))
				g [j] [i] = g [i] [j]


if __name__ == '__main__':
	# all configurable parameter(s).
	node_number = 4
	connection_probability = 0.2
	min_bw: int = 2
	max_bw: int = 5
	# all configurable parameter(s).

	# graph_2d.
	# a square graph = L * L.
	# nodes are randomly generated in the graph.
	L = 10.0
	X_list = [0.0] * node_number
	Y_list = [0.0] * node_number
	# rough calculation.
	connection_distance = round ((connection_probability * L * L / 4) ** 0.5, 1)
	max_dist = 0.0
	min_dist = math.ceil ((2 * L ** 2) ** 0.5)
	# equation parameters.
	a = b = c = 0.0

	"""
	we randomly generate nodes in a L * L big square where L = 10.
	we take each node (x1, y1) as the center to form a small square with side length = cd.
	when any other node (x2, y2) are distributed in this small square, we establish a connection
	between them.
	we ignore the situation where the nodes are distributed on the edge of the big square,
	and roughly think that the probability of other nodes falling on the small square is
	cp = (2 * cd / L) * (2 * cd / L), i.e., x2 in [x1 - cd, x1 + cd] and y2 in [y1 - cd, y1 + cd].
	so, cd = sqrt (cp * L * L / 4).
	"""

	g = np.zeros ((node_number, node_number))
	v = [0 for _ in range (node_number)]
	# graph_random ().
	graph_2d ()

	# check whether it is a connected graph.
	dfs ()
	# make sure it is connected.
	ensure_conn ()
	# distance to bw equation.
	calculate_equation ()
	assign_bw ()

	filename = os.path.abspath (os.path.join (os.path.dirname (__file__), 'bw.txt'))
	np.savetxt (filename, g.data, fmt='%.4f')
