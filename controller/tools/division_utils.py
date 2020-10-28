import os

import numpy as np
from tensorflow.keras.utils import to_categorical


def split_data (images, labels, batch, drop_last):
	"""
	split data into batch
	:param images: ndarrays.
	:param labels: ndarrays.
	:param batch: int, number of batches
	:param drop_last: if True, for an array of length l that should be split
    into n sections, it returns sub-arrays of size l/n, and drop rest data.
    if False, it returns l % n sub-arrays of size l/n + 1 and the rest of size l/n.
	:return: list of ndarrays.
	"""
	if drop_last:
		end_index = int (len (labels) / batch) * batch
	else:
		end_index = len (labels)
	images_loader = np.array_split (images [:end_index], batch)
	labels_loader = np.array_split (labels [:end_index], batch)
	return images_loader, labels_loader


def save_data (images_loader, labels_loader, path, one_hot):
	"""
	naming from 1 to n
	"""
	if not os.path.exists (path):
		os.makedirs (path)
	i = 1
	for images_data in images_loader:
		np.save (path + '/images_%d' % i, images_data)
		i += 1
	i = 1
	for labels_data in labels_loader:
		if one_hot:
			np.save (path + '/labels_%d' % i, to_categorical (labels_data))
		else:
			np.save (path + '/labels_%d' % i, labels_data)
		i += 1
