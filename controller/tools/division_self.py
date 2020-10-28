import json

import os
import argparse

from PIL import Image
import numpy as np
from tensorflow.keras.utils import to_categorical
from torch.utils.data import Dataset, DataLoader

parser = argparse.ArgumentParser ("自定义数据集处理脚本")
parser.add_argument ('-IS', '--input_sample_dir', dest='sample_dir', required=True,
	help='自定义数据集的样本数据存放文件夹的绝对路径')
parser.add_argument ('-IA', '--input_annotations_file', dest='annotations_file', required=True,
	help='自定义数据集的样本标签与样本数据文件名对应的标注json文件（文件名的前缀必须样本数据的文件名前缀相同）')
parser.add_argument ('-T', '--test', action='store_true', default=False,
	help='如果是加载测试数据集，则使用该选项')
args = parser.parse_args ()

sample_dir = args.sample_dir
annotations_file = args.annotations_file
is_test = args.test

# 数据存放文件夹
data_root = os.path.abspath (os.path.join (os.path.dirname (__file__), '../datasets/self'))
train_data_dir = os.path.join (data_root, 'train_data')
test_data_dir = os.path.join (data_root, 'test_data')


class SelfDataset (Dataset):
	"""
	用于加载自定义的数据集，需要输入自定义数据集的根目录、训练数据样本文件的存放目录以及带有样本数据文件名和标签的json文件名
	json文件格式：
	{
		"images":[,], // 样本数据文件名
		"categories":[,] // 样本数据标签（顺序需要与images数组一样）
	}
	"""

	def __init__ (self, root, src_data_dir, annotations_json, transform=None, target_transform=None):
		"""
		初始化函数
		:param root: 自定义数据集的根目录
		:param src_data_dir: 训练数据样本文件的存放目录
		:param annotations_json: 带有样本数据文件名和标签的json文件名
		:param transform: 是否对图片进行变换
		:param target_transform: 是否对目标进行变换 （未使用）
		"""
		super (SelfDataset, self).__init__ ()
		self.transform = transform
		self.target_transform = target_transform

		file_annotation = os.path.join (root, annotations_json)
		img_folder = os.path.join (root, src_data_dir)
		fp = open (file_annotation, 'r')
		data_dict = json.load (fp)
		assert len (data_dict ['images']) == len (data_dict ['categories'])
		num_data = len (data_dict ['images'])

		# 统计总共的category以及最小的category数字
		min_cat = int (data_dict ['categories'] [0])
		max_cat = int (data_dict ['categories'] [0])
		for cat in data_dict ['categories']:
			int_cat = int (cat)
			if int_cat < min_cat:
				min_cat = int_cat
			if int_cat > max_cat:
				max_cat = int_cat
		self.total_categories = abs (max_cat - min_cat) + 1
		self.min_category = min_cat

		self.data = []
		self.labels = []
		self.img_folder = img_folder
		for i in range (num_data):
			# 读取样本数据
			img_name = os.path.join (self.img_folder, data_dict ['images'] [i])
			src_img = Image.open (img_name)
			img_array = np.array (src_img, dtype=np.float32)
			self.data.append (img_array)

			# 转换category成np数组类型
			category = np.zeros (self.total_categories)
			category_index_of_one = int (data_dict ['categories'] [i]) - self.min_category
			category [category_index_of_one] = 1.
			self.labels.append (category)

	def __getitem__ (self, index):
		img_data = self.data [index]
		img_label = self.labels [index]

		if self.transform is not None:
			img_data = self.transform (img_data)

		return img_data, img_label

	def __len__ (self):
		return len (self.data)


if __name__ == '__main__':
	if not os.path.isdir (sample_dir) or not os.path.exists (annotations_file):
		print ('error path')
		exit (0)

	if not os.path.exists (train_data_dir):
		os.makedirs (train_data_dir)
	if not os.path.exists (test_data_dir):
		os.makedirs (test_data_dir)

	dataset = SelfDataset (data_root, sample_dir, annotations_file)
	if not is_test:
		batch_size = int (len (dataset) / 100)
		output_dir = train_data_dir
	else:
		batch_size = int (len (dataset))
		output_dir = test_data_dir
	loader = DataLoader (dataset, batch_size=batch_size, shuffle=True)

	idx = 0
	print ('loading data set, total number: {}'.format (len (dataset)))
	for data in loader:
		img, label = data
		img = img.numpy ()
		np.save (output_dir + 'images_{}'.format (idx), img)
		label = label.numpy ()
		label = to_categorical (label)
		np.save (output_dir + 'labels_{}'.format (idx), label)
		idx += 1
