## env_tree.txt
- type  
0：EL，1：FL.  
- worker_fraction  
in EL, set worker_fraction equal to 1.  
in FL, set worker_fraction in range (0, 1].  
- node_list  
breadth first traversal of FL or EL structure.  
```
"node_list": [
{"name": "n1", "layer": 3, "sync": 5, "down_num": 2},
{"name": "n2", "layer": 2, "sync": 2, "down_num": 2},
{"name": "n4", "layer": 2, "sync": 2, "down_num": 2},
{"name": "n2", "layer": 1, "epoch": 4},
{"name": "n3", "layer": 1, "epoch": 4},
{"name": "n4", "layer": 1, "epoch": 4},
{"name": "d1", "layer": 1, "epoch": 1}]
```
Line 1: when n1 ("name": "n1") acts on the 3rd layer ("layer": 3),
it uploads weights (actually completes training because it's the top node)
after 5 aggregations ("sync": 5), and it has 2 child nodes ("down_num": 2).  
Line 2: when n2 acts on the 2nd layer, it uploads weights after 2 aggregations,
and it has 2 child nodes.  
Line 4: when n2 acts on the 1st layer as trainer, it uploads weights after 4 local epoch trainings.  
## env_datasets.txt
we assume that the train-set and test-set are spat by ```contorller/tools/splitter_utils.py```,
and they are named like test_data/images_(1 to 100).npy,  test_data/labels_(1 to 100).npy,
 train_data/images_(1 to 100).npy and train_data/labels_(1 to 100).npy.  
- order  
how we map the following values in list to node.  
```"order": ["n1", "n2", "n3", "n4", "d1"]```
- batch_size  
set to 0 for nodes that don't act on the 1st layer.  
```"batch_size": [0, 32, 32, 32, 8]```  
1st item means that n1 doesn't act on the 1st layer.  
2nd item means that n2 has bach_size=32 when acts on the 1st layer as trainer.  
- train_start_i, train_len  
set to 0 for nodes that don't act on the 1st layer.
```"train_start_i": [0, 1, 11, 21, 31]```  
```"train_len": [0, 10, 10, 10, 10]```  
1st item means that n1 doesn't act on the 1st layer.  
2nd item means to allocate train_data/images_(1 to 10).npy
and train_data/labels_(1 to 10).npy to n2.
- test_start_i, test_len  
set to 0 for nodes that only act on the 1st layer.
```"test_start_i": [1, 11, 0, 21, 0]```  
```"test_len": [10, 10, 0, 10, 0]```  
