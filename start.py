import os
import threading


def hybrid (node_id):
	os.system ('python hybrid.py -i ' + str (node_id))


# 与hybrid.py中测试内容的节点数相等
number = 4
for index in range (number):
	threading.Thread (target=hybrid, args=(index,)).start ()
