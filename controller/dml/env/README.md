## .env
use n2 as example
- type  
0：EL，1：FL.  
```"type": 0```  
- layer  
acts on these layers.  
```"layer": [1, 2]```  
n2 acts on 1st layer and 2nd layer.  
- worker_fraction  
in EL, set worker_fraction equal to 1.  
in FL, set worker_fraction in range (0, 1].  
```worker_fraction: 1```  
- up_node  
set to "self" when upper node is itself
and set to "top" when it's the top node.  
```"up_node": ["self","n1"]```  
when acts on 1st layer, n2's upper node is itself
and when acts on 2nd layer, n2's upper node is n1.  
- down_node  
```"down_node": [[], ["self", "n3"]]```  
when acts on 1st layer, n2 doesn't have child node
and when acts on 2nd layer, n2 has two child nodes, i.e., itself and n3.  
- sync  
set to 0 when acts on 1st layer as trainer.  
```"sync": [0, 2]```  
when acts on 1st layer, n2 doesn't need sync
and when acts on 2nd layer, n2 uploads weights after 2 aggregations.  
- epoch  
set to 0 for nodes that don't act on the 1st layer.  
```"epoch": 4```  
when acts on 1st layer, n2 uploads weights after 4 local epoch trainings.  

- batch_size  
set to 0 for nodes that don't act on the 1st layer.  
```"batch_size": 32```  
n2 has bach_size=32 when acts on the 1st layer as trainer.  
- train_start_i, train_len  
set to 0 for nodes that don't act on the 1st layer.  
```"train_start_i": 1```  
```"train_len": 10```  
allocate train_data/images_(1 to 10).npy and train_data/labels_(1 to 10).npy to n2.  
- test_start_i, test_len  
set to 0 for nodes that only act on the 1st layer.  
```"test_start_i": 11```  
```"test_len": 10```  
allocate test_data/images_(11 to 20).npy and test_data/labels_(11 to 20).npy to n2.  

This part depends on ```contorller/bw.txt``` and ```contorller/node_ip.txt```  
- connect  
destination node: destination address.  
```"connect": {'n1': 'http://s-n1:8001', 'n3': 'http://s-n3:8003', 'd1': 'http:192.168.1.13:8888'}```  
n2 can directly send messages to n1, n3 and d1.  
- forward  
destination node: next hop's address.  
```"forward": {'n4': 'http://s-n1:8001'}```  
if n2 want to send messages to n4, it should sent to d1
and d1 will send the message to n4 (and may still need to be forwarded).  
