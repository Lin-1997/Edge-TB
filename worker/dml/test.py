import os

# os.environ ["CUDA_VISIBLE_DEVICES"] = "-1"

from nns.nn_cifar10 import nn
# from nns.nn_mnist import nn
from utils import load_data

model = nn.model
input_shape = nn.input_shape

start_i = 1
_len = 3
path = 'datasets/CIFAR10/train_data'
train_images, train_labels = load_data (path, start_i, _len, input_shape)

start_i = 1
_len = 20
path = 'datasets/CIFAR10/test_data'
test_images, test_labels = load_data (path, start_i, _len, input_shape)

_sum = 1
for i in input_shape [1:]:
	_sum *= i
for i in range (1, len (model.layers)):
	shape = model.get_layer (index=i).output_shape [1:]
	temp = 1
	for a in shape:
		temp *= a
	_sum += temp
print ('# layer outputs=' + str (_sum))

model.summary ()
# model.fit (train_images, train_labels, epochs=15, validation_data=(test_images, test_labels))
model.fit (train_images, train_labels, epochs=10, batch_size=8)
# model.test_on_batch (test_images, test_labels)
