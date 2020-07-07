import getopt
import random
import sys

import numpy as np


def random_g ():
	for i in range (n):
		for j in range (i, n):
			if i == j:
				g [i] [j] = float ('inf')
			elif random.random () <= conn_prob:
				g [i] [j] = format (random.uniform (min_bw, max_bw), '.2f')
				g [j] [i] = g [i] [j]


def no_conn ():
	for val in range (len (v)):
		if v [val] == 0:
			return val
	return 0


def dfs (i_node):
	v [i_node] = 1
	for i_next in range (n):
		if v [i_next] == 0 and g [i_node] [i_next] > 0:
			dfs (i_next)


n = 4
conn_prob = 0.2
min_bw = 2
max_bw = 10

try:
	opts, args = getopt.getopt (sys.argv [1:], 'n:p:b:t:', ['number=', 'prob=', 'button=', 'top='])
except getopt.GetoptError:
	sys.exit (1)
for opt, arg in opts:
	if opt in ('-n', '--number'):
		n = int (arg)
	elif opt in ('-p', '--prob'):
		conn_prob = float (arg)
	elif opt in ('-b', '--button'):
		min_bw = int (arg)
	elif opt in ('-t', '--top'):
		max_bw = int (arg)

g = np.zeros ((n, n))
v = [0 for _ in range (n)]
random_g ()
dfs (0)

start = no_conn ()
while start != 0:
	v_temp = []
	for i_temp in range (n):
		if v [i_temp] == 1:
			v_temp.append (i_temp)
	random.shuffle (v_temp)
	for index in v_temp:
		if v [index] == 1 and g [start] [index] == 0:
			g [start] [index] = format (random.uniform (min_bw, max_bw), '.2f')
			g [index] [start] = g [start] [index]
			v [start] = 1
			break
	dfs (start)
	start = no_conn ()

print (g)
np.savetxt ('np_graph.txt', g, fmt='%.2f')
