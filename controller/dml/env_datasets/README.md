## .env
- batch_size  
set to 0 for nodes that don't act on the 1st layer.  
```"batch_size": 32```  
this node has bach_size=32 when acts on the 1st layer as trainer.  
- train_start_i, train_len  
set to 0 for nodes that don't act on the 1st layer.  
```"train_start_i": 1```  
```"train_len": 10```  
allocate train_data/images_(1 to 10).npy and train_data/labels_(1 to 10).npy to this node.  
- test_start_i, test_len  
set to 0 for nodes that only act on the 1st layer.  
```"test_start_i": 1```  
```"test_len": 10```  
allocate test_data/images_(1 to 10).npy and test_data/labels_(1 to 10).npy to this node.  
