import random

import numpy as np


def random_g ():
	for i in range (switch_n):
		for j in range (i, switch_n):
			if i == j:
				g [i] [j] = float ('inf')
			elif random.random () <= conn_prob:
				g [i] [j] = format (random.uniform (switch_min_bw, switch_max_bw), '.2f')
				g [j] [i] = g [i] [j]


def no_conn ():
	for val in range (len (v)):
		if v [val] == 0:
			return val
	return 0


def dfs (i_node):
	v [i_node] = 1
	for i_next in range (switch_n):
		if v [i_next] == 0 and g [i_node] [i_next] > 0:
			dfs (i_next)


# 交换机数量
switch_n = 4
# 交换机相互连接概率
conn_prob = 0.2
# 带宽下限
switch_min_bw = 0.002
# 带宽上限
switch_max_bw = 0.003
# 节点数量
host_n = 4
host_min_bw = 0.002
host_max_bw = 0.003

g = np.zeros ((switch_n, switch_n))
v = [0 for _ in range (switch_n)]
random_g ()
dfs (0)

start = no_conn ()
while start != 0:
	v_temp = []
	for i_temp in range (switch_n):
		if v [i_temp] == 1:
			v_temp.append (i_temp)
	random.shuffle (v_temp)
	for index in v_temp:
		if v [index] == 1 and g [start] [index] == 0:
			g [start] [index] = format (random.uniform (switch_min_bw, switch_max_bw), '.4f')
			g [index] [start] = g [start] [index]
			v [start] = 1
			break
	dfs (start)
	start = no_conn ()

print (g)
np.savetxt ('switch_bw.txt', g.data, fmt='%.4f')

host = {"conn": [], "bw": []}
temp_switch = list (range (1, switch_n + 1))
for index in range (host_n):
	switch_value = random.choice (temp_switch)
	temp_switch.remove (switch_value)
	if len (temp_switch) == 0:
		temp_switch = list (range (1, switch_n + 1))
	host ['conn'].append (switch_value)
	host ['bw'].append (float (format (random.uniform (host_min_bw, host_max_bw), '.4f')))

f = open ('host_conn.txt', 'w')
f.write (str (host))
f.write ('\r\n')
print (host)
f.close ()
