## env.txt文件说明
- 交换机的部署  
```"switch_number": [4]```  
例如```[4, 5, 8]```表示1~4部署在物理机1，5~5部署在物理机2，6~8部署在物理机3
- 节点的部署  
```"host_number": [4]```  
- etree广度优先遍历  
```
"host_list": [
	{"id": 1, "dc": 2, "layer": 3, "sync": 10},
	{"id": 1, "dc": 2, "layer": 2, "sync": 2},
	{"id": 3, "dc": 2, "layer": 2, "sync": 2},
	{"id": 1, "dc": 0, "layer": 1, "sync": 0},
	{"id": 2, "dc": 0, "layer": 1, "sync": 0},
	{"id": 3, "dc": 0, "layer": 1, "sync": 0},
	{"id": 4, "dc": 0, "layer": 1, "sync": 0}]
```
第一行：节点1，有两个子节点，处在第三层，聚合10次  
示例对应的etree网络见```etree/node/env/n_network.png```  
- 各种参数  
```"round": [20, 20, 20, 20]```  
根据id大小升序表示节点的各种参数  

## switch_bw.txt文件说明
交换机连接的二位矩阵，数值表示带宽，单位MB/s，inf表示和自身的连接，0表示没有连接  
示例对应的网络见```etree/switch/env/s_network.png```  

## host_conn.txt文件说明
- 根据节点id大小升序表示每个节点连到第几个交换机  
```'conn': [2, 1, 4, 3]```  
- 根据节点id大小升序表示连接的带宽  
```'bw': [0.002, 0.002, 0.002, 0.002]```  
示例对应的网络见```etree/switch/env/s_network.png```  
