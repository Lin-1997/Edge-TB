import os

import numpy as np
from keras.utils import to_categorical
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

data_root = os.path.abspath (os.path.join (os.path.dirname (__file__), '../../node/datasets'))
train_dir = data_root + '/MNIST/train_data/'
test_dir = data_root + '/MNIST/test_data/'

# 创建保存文件路径
if not os.path.exists (train_dir):
	os.makedirs (train_dir)
if not os.path.exists (test_dir):
	os.makedirs (test_dir)

# pytorch自带的读取MNIST数据的函数
data_tf = transforms.Compose ([transforms.ToTensor ()])
train_dataset = datasets.MNIST (root=data_root, train=True, transform=data_tf, download=True)
test_dateset = datasets.MNIST (root=data_root, train=False, transform=data_tf, download=True)

# 每份的样本数
batch_size = int (len (train_dataset) / 100)

# pytorch的数据加载器
train_loader = DataLoader (train_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
test_loader = DataLoader (test_dateset, batch_size=len (test_dateset), shuffle=True)

idx = 0
print ('loading training set, total number: {}'.format (len (train_dataset)))
for data in train_loader:
	img, label = data
	# 从tensor类型转换为numpy格式
	img = img.numpy ()
	np.save (train_dir + 'images_{}'.format (idx), img)
	label = label.numpy ()
	# 转换为One-hot编码
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
