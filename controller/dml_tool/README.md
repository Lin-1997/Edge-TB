## gl_structure.json

```
{
  "sync": 75,
  "node_list": [
    {"name": "p1", "epoch": 1},
    {"name": "n1", "epoch": 1},
    {"name": "n2", "epoch": 1},
    {"name": "n3", "epoch": 1},
    {"name": "n4", "epoch": 1}
  ]
}
```

Each node will no longer _Gossip_ after 75 rounds of training ("sync": 75), but it can still receive models from others
for training.  
p1 _Gossip_ after 1 local epoch trainings ("epoch": 1).

## fl_structure.json

```
{
  "node_list": [
    {"name": "n1", "trainer_fraction": 0.5, "sync": 75},
    {"name": "n2", "epoch": 1},
    {"name": "n3", "epoch": 1},
    {"name": "n4", "epoch": 1},
    {"name": "p1", "epoch": 1}
  ]
}
```

The first node is the aggregator and other nodes are trainers.  
The aggregator completes training after 75 aggregations ("sync": 75).  
In each round, the aggregator sends weights to about 50% of trainers ("trainer_fraction": 0.5).  
n2 uploads weights (if selected) after 1 local epoch trainings ("epoch": 1).

## el_structure.json

```
{
  "node_list": [
    {"name": "n1", "layer": 3, "sync": 25, "child_num": 2},
    {"name": "n1", "layer": 2, "sync": 4, "child_num": 2},
    {"name": "n2", "layer": 2, "sync": 4, "child_num": 3},
    {"name": "n1", "layer": 1, "epoch": 1},
    {"name": "p1", "layer": 1, "epoch": 1},
    {"name": "n2", "layer": 1, "epoch": 1},
    {"name": "n3", "layer": 1, "epoch": 1},
    {"name": "n4", "layer": 1, "epoch": 1}
  ]
}
```

Breadth first traversal of layered structures.  
Line-1: when n1 ("name": "n1") acts in the 3rd layer ("layer": 3) as aggregator (abbreviated as n1-3rd), it completes
training after 25 aggregations ("sync": 25). n1-3rd has 2 child nodes ("child_num": 2).  
Subsequent nodes in the 2nd layer will become children of n1-3rd until the requirements of n1-3rd are met, i.e., Line-2
and Line-3.  
Line-2: n1-2nd uploads weights after 4 aggregations, and it has 2 child nodes, i.e., Line-4 and Line-5.  
Line-3: n2-2nd uploads weights after 4 aggregations, and it has 2 child nodes, i.e., Line-6, Line-7, and Line-8.  
Line-4: when n1 acts in the 1st layer as trainer, it uploads weights after 1 local epoch trainings.

## ra_structure.json

```
{
  "sync": 75,
  "node_list": [
    {"name": "p1", "epoch": 1},
    {"name": "n1", "epoch": 1},
    {"name": "n2", "epoch": 1},
    {"name": "n3", "epoch": 1},
    {"name": "n4", "epoch": 1}
  ]
}
```

Each node sends weights to the previous node, e.g., n1 sends to p1 and n2 sends to n1.  
For the first node, it sends weights to the last node, i.e., p1 sends to n4.  
Each node will no longer send weights after 75 rounds of training ("sync": 75).  
p1 starts the next round after 1 local epoch trainings ("epoch": 1).

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
