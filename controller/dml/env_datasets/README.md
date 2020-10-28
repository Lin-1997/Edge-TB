## .env文件说明
- 训练参数  
```"batch_size": 16```  
不作为训练节点时赋值为0  
- 训练样本起始文件下标和文件个数  
```"train_start_i": 1```  
```"train_len": 2```  
即使用train_images_1.npy、train_images_2.npy以及train_labels_1.npy、train_labels_2.npy  
不作为训练节点时两个都赋值为0  
- 测试样本起始文件下标和文件个数  
```"test_start_i": 5```  
```"test_len": 1```  
即使用test_images_5.npy以及test_labels_5.npy  
不作为聚合节点时两个都赋值为0  
## 注意
在master划分数据集后，会生成一个不完整的.env，只有上述五个内容，
master完成建树后会发送完整的.env文件覆盖不完整的.env  
