## .env文件说明
- 训练参数  
```"learning_rate": 0.05```    
```"batch_size": 10```  
- 训练样本范围，\[start_index, end_index]  
```"start_index": 0```  
```"end_index": 1```  

## 注意
在master划分数据集后，会生成一个不完整的.env，只有上述四个内容，
master完成建树后会发送完整的.env文件覆盖不完整的.env  