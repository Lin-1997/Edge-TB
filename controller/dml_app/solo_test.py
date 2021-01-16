"""
you can use this file to test your neural network models
and datasets on a single computer.
"""

import os

from dml_utils import load_data
from nns.nn_mnist import nn  # configurable parameter, from nns.whatever import nn

# configurable parameter, uncomment to disable GPUs.
# os.environ ["CUDA_VISIBLE_DEVICES"] = "-1"

model = nn.model
input_shape = nn.input_shape
dirname = os.path.abspath (os.path.dirname (__file__))

train_start_i = 1
train_len = 3
# configurable parameter, specify the dataset path
train_path = os.path.join (dirname, 'datasets/MNIST/train_data')
train_images, train_labels = load_data (train_path, train_start_i, train_len, input_shape)

test_start_i = 1
test_len = 20
# configurable parameter, specify the dataset path
test_path = os.path.join (dirname, 'datasets/MNIST/test_data')
test_images, test_labels = load_data (test_path, test_start_i, test_len, input_shape)

model.summary ()
# model.fit (train_images, train_labels, epochs=15, validation_data=(test_images, test_labels))
model.fit (train_images, train_labels, epochs=10, batch_size=8)
# loss, acc = model.test_on_batch (test_images, test_labels)
