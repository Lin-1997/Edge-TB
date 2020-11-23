"""
this file loads cifar10 from keras and cut the data into several pieces in sequence.
"""
import os

import numpy as np
from tensorflow.keras.datasets import cifar10

from splitter_utils import split_data, save_data

if __name__ == '__main__':
	# all configurable parameters.
	train_batch = 100
	train_drop_last = True
	test_batch = 100
	test_drop_last = True
	one_hot = False
	# all configurable parameters.

	# load data from keras.
	(train_images, train_labels), (test_images, test_labels) = cifar10.load_data ()
	# normalize.
	train_images, test_images = train_images / 255.0, test_images / 255.0
	# convert to float32.
	train_images, test_images = train_images.astype (np.float32), test_images.astype (np.float32)

	# save in here.
	path = os.path.abspath (os.path.join (os.path.dirname (__file__), '../datasets/CIFAR10'))
	train_path = os.path.join (path, 'train_data')
	test_path = os.path.join (path, 'test_data')

	# split and save.
	train_images_loader, train_labels_loader = split_data (train_images, train_labels, train_batch, train_drop_last)
	save_data (train_images_loader, train_labels_loader, train_path, one_hot)

	test_images_loader, test_labels_loader = split_data (test_images, test_labels, test_batch, test_drop_last)
	save_data (test_images_loader, test_labels_loader, test_path, one_hot)
