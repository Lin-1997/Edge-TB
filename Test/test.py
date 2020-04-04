import tensorflow as tf
import numpy as np

w1 = tf.truncated_normal([2, 2, 2, 2])
w2 = tf.truncated_normal([2, 2, 2, 2])
sess = tf.Session()
list1 = []
list1.append(sess.run(w1))
list2 = []
list2.append(sess.run(w2))
received_client_weight = []
received_client_weight.append(list1)
received_client_weight.append(list2)
print(received_client_weight)
total_weight = received_client_weight[0]
for weight_index in range(1, len(received_client_weight)):
	tmp_weight = []
	this_weight = received_client_weight[weight_index]
	for i in range(len(total_weight)):
		tmp_weight.append(np.sum([total_weight[i], this_weight[i]], axis=0))
	total_weight = tmp_weight
received_client_count = 2
avg_weight = [each_total_weight / received_client_count for each_total_weight in total_weight]
print(avg_weight)