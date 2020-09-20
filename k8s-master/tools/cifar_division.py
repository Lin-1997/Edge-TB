import os

import numpy as np
from keras.utils import to_categorical
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

ten = True  # The only configurable parameter, True for cifar-10, False for cifar-100

if ten:
	data_root = os.path.abspath (os.path.join (os.path.dirname (__file__), '../../node/datasets/CIFAR10'))
else:
	data_root = os.path.abspath (os.path.join (os.path.dirname (__file__), '../../node/datasets/CIFAR100'))
train_dir = data_root + '/train_data/'
test_dir = data_root + '/test_data/'

if not os.path.exists (train_dir):
	os.makedirs (train_dir)
if not os.path.exists (test_dir):
	os.makedirs (test_dir)

data_tf = transforms.Compose ([transforms.ToTensor ()])
if ten:
	train_dataset = datasets.CIFAR10 (root=data_root, train=True, transform=data_tf, download=True)
	test_dateset = datasets.CIFAR10 (root=data_root, train=False, transform=data_tf, download=True)
else:
	train_dataset = datasets.CIFAR100 (root=data_root, train=True, transform=data_tf, download=True)
	test_dateset = datasets.CIFAR100 (root=data_root, train=False, transform=data_tf, download=True)

batch_size = int (len (train_dataset) / 100)

train_loader = DataLoader (train_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
test_loader = DataLoader (test_dateset, batch_size=len (test_dateset), shuffle=True)

idx = 0
print ('loading training set, total number: {}'.format (len (train_dataset)))
for data in train_loader:
	img, label = data
	img = img.numpy ()
	np.save (train_dir + 'images_{}'.format (idx), img)
	label = label.numpy ()
	label = to_categorical (label)
	np.save (train_dir + 'labels_{}'.format (idx), label)
	idx += 1

print ('loading test set, total number: {}'.format (len (test_dateset)))
for data in test_loader:
	img, label = data
	img = img.numpy ()
	np.save (test_dir + 'images', img)
	label = label.numpy ()
	label = to_categorical (label)
	np.save (test_dir + 'labels', label)
