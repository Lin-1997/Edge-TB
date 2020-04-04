import tensorflow as tf

def add_layer(weight_assign_op_list, inputs, in_size, out_size, activation_function=None):
	weights = tf.Variable(tf.random_normal([in_size, out_size]))
	weight_holder = tf.placeholder(tf.float32, [in_size, out_size])
	weight_assign_op_list.append(tf.assign(weights, weight_holder))
	biases = tf.Variable(tf.zeros([1, out_size]) + 0.1)
	biases_holder = tf.placeholder(tf.float32, [1, out_size])
	weight_assign_op_list.append(tf.assign(biases, biases_holder))
	wx_plus_b = tf.matmul(inputs, weights) + biases
	if activation_function is None:
		outputs = wx_plus_b
	else:
		outputs = activation_function(wx_plus_b)
	return outputs
