## .env文件说明
- 类型，0：EL，1：FL  
```"type": 0```  
conf_gen.py生成的默认type=0  
- 同时处于多少层  
```"layer_count": 3```

- 下面例子中使用[ ]为key值的，即使节点只处于一层也要用[ ]  

- 分别属于哪些层，1为最底层  
```"layer": [1,2,3]```  
EL中节点可以同时负责训练和聚合，但FL中不要让聚合节点同时作为训练节点  
- 节点位于每层的上层节点  
```"up_host": ["self","self","top"]```  
当节点上层节点仍为自己时，该层up_host置为self  
当节点处于最顶层时，该层up_host置为top  
- 节点位于每层的下层节点数量  
```"down_count": [0,2,2]```  
当节点处于最底层为训练节点时，该层的down_count置为0  
- 节点位于每层的下层节点  
```"down_host": [[],["self","r1"],["self","n2"]]```  
即使节点只处于一层也要用[[ ]]  
- EL中每层的同步频率  
```"sync": [0,2,10]```  
当节点处于最底层为训练节点时，该层的sync置为0  
当节点处于最顶层时，该层sync控制整个训练过程的聚合次数，当最顶层达到sync次聚合后，训练结束  

- 本地训练次数  
```"local_epoch_num": 1```  
不作为训练节点时赋值为0  
- 训练参数  
```"batch_size": 8```  
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
- FL聚合节点专用，每轮选多少比例的节点训练，EL固定赋值为1，FL赋值0~1之间  
```"worker_fraction: 1"```  

- 自动生成的路由信息  
- 直连的节点  
```"node": {'r1': 'http://192.168.0.108:8888', 'n3': 'http://s-n3:8003'}```  
目标host_name: 目标path  
- 需要别人转发的节点  
```"forward": {'n2': 'http://s-n3:8003'}```  
目标host_name: 下一跳帮转发的path  
