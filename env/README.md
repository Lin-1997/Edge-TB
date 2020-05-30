####当前env的网络结构
![网络结构](../default_network.png)

#### env文件说明
- id，要和该env的名字一致  
```"id": 1```
- 端口号，统一8888  
```"port": 8888```
- 类型，0: EL，1: FL  
```"type": 0```
- 同时处于多少层  
```"layer_count": 3```

- 下面例子中使用[ ]为key值的，即使节点只处于一层也要用[ ]，参考n2.env
  
- 分别属于哪些层，1为最底层  
```"layer": [1,2,3]```  
注意，EL中节点可以同时负责训练和聚合，但FL中不要让聚合节点同时作为训练节点
- 节点位于每层的上层节点地址  
```"up_addr": ["self","self","top"]```  
当节点同时处于多层，且上层节点仍为自己时，用self代替完全的地址  
当节点处于最顶层时，该层up_addr置为top
- 节点位于每层的下层节点数量  
```"down_count": [0,2,2]```  
当节点处于最底层为训练节点时，该层的down_count置为0  
- 节点位于每层的下层节点地址  
```"down_addr": [[],["self","http://10.0.0.2:8888"],["self","http://10.0.0.3:8888"]]```  
```"down_addr_host": [[],["self","http://n2:8888"],["self","http://n3:8888"]]```  
当节点仅仅处于最底层时可以不写down_addr和down_addr_host  
当节点同时处于最底层和其他层时，最底层要留一个空的[ ]，如上  
当节点同时处于多层，且下层节包含自己时，用self代替完全的地址，如上  
当节点只处于一层时，也要用[[ ]]，如下  
```"down_addr": [["self","http://10.0.0.2:8888"]]```  
```"down_addr_host": [["self","http://n2:8888"]]```  
down_addr是containernet用的，down_addr_host是docker-compose用的  
区别在于一个是containernet.py里面的ip，一个是run.yml里面的HOSTNAME  
可以只写使用到的一种
- EL中每层的同步频率  
```"sync": [0,2,10]```  
当节点处于最底层为训练节点时，该层的sync置为0  
当节点处于最顶层时，该层sync控制整个训练过程的聚合次数，当最顶层达到sync次聚合后，训练结束  

- 下面这几个不是训练节点可以不写  
- 用来将训练数据划分成一定数量的batch，正考虑换个名称  
```"round": 20```
- 本地训练次数  
```"local_epoch_num": 1```  
本地训练多少次后上传到聚合节点
- 每次训练用多少个样本  
```"batch_size": 1```
- 学习率  
```"learning_rate": 0.05```
- 训练样本范围，在nn_lr中不起作用，但也要写，[start_index, end_index)  
```"start_index": 0```  
```"end_index": 1```

- FL聚合节点专用，每轮选多少比例的节点训练，EL中赋值为1，或者删除掉  
```"worker_fraction: 0.5"```