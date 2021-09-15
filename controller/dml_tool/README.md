## gl_structure.json

```
{
"sync": 30,
"node_list": [
{"name": "p1", "epoch": 1},
{"name": "p2", "epoch": 4},
{"name": "p3", "epoch": 7},
{"name": "n1", "epoch": 2}]
}
```

Each node will no longer _Gossip_ after 30 rounds of training ("sync": 30), but it can still receive models from others
for training.  
p2 _Gossip_ after 4 local epoch trainings ("epoch": 4).

## fl_structure.json

```
{
"node_list": [
{"name": "p4", "trainer_fraction": 0.2, "sync": 75},

{"name": "p1", "epoch": 1},
{"name": "p2", "epoch": 3},
{"name": "p3", "epoch": 1},
{"name": "n1", "epoch": 2},
{"name": "n2", "epoch": 7},
{"name": "n3", "epoch": 5}]
}
```

The first node is the aggregator and other nodes are trainers.  
The aggregator uploads weights (actually completes training) after 75 aggregations ("sync": 75).  
In each round, the aggregator sends weights to about 20% of trainers ("trainer_fraction": 0.2).  
p2 uploads weights (if selected) after 3 local epoch trainings ("epoch": 3).

## el_structure.json

```
{
"node_list": [
{"name": "n1", "layer": 3, "sync": 5, "child_num": 2},
{"name": "n2", "layer": 2, "sync": 2, "child_num": 2},
{"name": "n4", "layer": 2, "sync": 2, "child_num": 3},
{"name": "n2", "layer": 1, "epoch": 4},
{"name": "n3", "layer": 1, "epoch": 4},
{"name": "n4", "layer": 1, "epoch": 4},,
{"name": "d1", "layer": 1, "epoch": 1}
{"name": "d2", "layer": 1, "epoch": 1}]
}
```

Breadth first traversal of layered structures.  
Line 1: when n1 ("name": "n1") acts in the 3rd layer ("layer": 3), it uploads weights (actually completes training
because it's the top node) after 5 aggregations ("sync": 5). n1 has 2 child nodes ("child_num": 2) in the 3rd layer
including the nodes in the following two lines (n2 and n4).  
Line 2: when n2 acts in the 2nd layer, it uploads weights after 2 aggregations, and it has 2 child nodes.  
Line 4: when n2 acts in the 1st layer as trainer, it uploads weights after 4 local epoch trainings.

## dataset.json

```"n1": {"test_len": 100, "test_start_index": 1, "batch_size": 32}```  
Allocate 100 test-sets of 1~100, 0 train-set to n1. Set the batch size to 32.

```"n2": {"train_len": 10, "train_start_index": 21, "batch_size": 16}```  
Allocate 0 test-set, 10 train-sets of 21~30 to n2. Set the batch size to 16.

```"n3":{"test_len": 5, "test_start_index": 1, "train_len": 20, "train_start_index": 3, "batch_size": 64}```  
Allocate 5 test-sets of 1~5, 20 train-sets of 3~22 to n3. Set the batch size to 64.

## .log

Train: loss={}, round={},  
Aggregate: accuracy={}, round={},  
Aggregate: accuracy={}, round={}, layer={},    
