"""
you can use this file to test your neural network models
and datasets on a single computer.
"""

import os

import dml_utils
# from nns.nn_mnist import nn
from nns.nn_cifar10 import nn
# from nns.nn_fashion_mnist import nn

# configurable parameter, uncomment to disable GPUs.
# os.environ ["CUDA_VISIBLE_DEVICES"] = "-1"

dirname = os.path.abspath (os.path.dirname (__file__))

nn.model.summary ()

batch_size = 32
train_len = 100
train_start_index = 1
# configurable parameter, specify the dataset path
# train_path = os.path.join (dirname, '../dataset/MNIST/train_data')
train_path = os.path.join (dirname, '../dataset/CIFAR10/train_data')
# train_path = os.path.join (dirname, '../dataset/FASHION_MNIST/train_data')
train_images, train_labels = dml_utils.load_data (train_path, train_start_index, train_len, nn.input_shape)

test_len = 5
test_start_index = 1
# configurable parameter, specify the dataset path
# test_path = os.path.join (dirname, '../dataset/MNIST/test_data')
test_path = os.path.join (dirname, '../dataset/CIFAR10/test_data')
# test_path = os.path.join (dirname, '../dataset/FASHION_MNIST/test_data')
test_images, test_labels = dml_utils.load_data (test_path, test_start_index, test_len, nn.input_shape)

loss_list = dml_utils.train_all (nn.model, train_images, train_labels, 50, batch_size)
# loss, acc = dml_utils.test (nn.model, test_images, test_labels)
loss, acc = dml_utils.test_on_batch (nn.model, test_images, test_labels, batch_size)
print ('loss = ' + str (loss) + ', acc = ' + str (acc))