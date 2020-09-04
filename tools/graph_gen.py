import random
import math
import numpy as np
from numpy.linalg import solve


def g_random ():
	for i in range (node_n):
		for j in range (i, node_n):
			if i == j:
				g [i] [j] = float ('inf')
			elif random.random () <= conn_prob:
				g [i] [j] = round (random.uniform (min_bw, max_bw), 2)
				g [j] [i] = g [i] [j]


def g_2d ():
	global max_dist, min_dist
	for i in range (node_n):
		g [i] [i] = float ('inf')
		x1 = round (random.uniform (0, X), 1)
		y1 = round (random.uniform (0, X), 1)
		X_list [i] = x1
		Y_list [i] = y1
		for j in range (i):
			x2 = X_list [j]
			y2 = Y_list [j]
			if x1 - conn_dist <= x2 <= x1 + conn_dist and y1 - conn_dist <= y2 <= y2 + conn_dist:
				dist = round (((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5, 4)
				if dist > max_dist:
					max_dist = dist
				if dist < min_dist:
					min_dist = dist
				g [i] [j] = dist
				g [j] [i] = g [i] [j]


def dfs (i_node=0):
	v [i_node] = 1
	for i_next in range (node_n):
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
		for i in range (node_n):
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


def cal_abc ():
	global a, b, c
	cal1 = np.mat ([[min_dist ** 2, min_dist, 1], [(min_dist + max_dist) ** 2 / 16, (min_dist + max_dist) / 4, 1],
	                [max_dist ** 2, max_dist, 1]])
	cal2 = np.mat ([0, (max_bw - min_bw) / 3, max_bw - min_bw]).T
	result = solve (cal1, cal2).tolist ()
	a = round (result [0] [0], 4)
	b = round (result [1] [0], 4)
	c = round (result [2] [0], 4)


def assign_bw ():
	# print ('max_dist=' + str (max_dist))
	# print ('min_dist=' + str (min_dist))
	print ('cal=' + str (a) + '*dist^2 + ' + str (b) + '*dist + ' + str (c))
	for i in range (node_n):
		for j in range (i):
			if i == j:
				continue
			elif g [i] [j] != 0.0:
				g [i] [j] = max (min_bw, round (max_bw - a * g [i] [j] ** 2 - b * g [i] [j] - c, 4))
				g [j] [i] = g [i] [j]


# 节点数量
node_n = 4
# 节点相互连接概率
conn_prob = 0.2
# 带宽下限
min_bw = 0.001
# 带宽上限
max_bw = 0.01

# g_2d
# 图大小
X = 10.0
X_list = [0.0] * node_n
Y_list = [0.0] * node_n
# 连接距离
conn_dist = round ((conn_prob * X ** 2 / 4) ** 0.5, 1)
max_dist = 0.0
min_dist = math.ceil ((2 * X ** 2) ** 0.5)
# 距离网速方程组
a = b = c = 0.0

# 初始化g
g = np.zeros ((node_n, node_n))
v = [0 for _ in range (node_n)]
# 赋值
# g_random ()
g_2d ()

# 检测是否连通图
dfs ()
# 确保连通
ensure_conn ()
# 距离网速方程组
cal_abc ()
# 赋值网速
assign_bw ()

print (g)
np.savetxt ('node_bw.txt', g.data, fmt='%.4f')
