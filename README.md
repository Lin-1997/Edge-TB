### Installation
0. At least 2 computers, each with 2-cores and 2G memory, one acts as Master and others act as Nodes  
0. Linux required, Ubuntu recommended  
0. Install python3 and python3-pip  
0. Install K8s and Docker. For Chinese users, look https://www.jianshu.com/p/f2d4dd4d1fb1 for details  
0. On Master  
    0. Type ```kubeadm config images list```  to list the suitable versions, and modify ```etree/k8s-master/setup.sh```  
    0. The docker image can be obtained through the official registry  
    0. For Chinese users, it may be better to use ```registry.aliyuncs.com/google_containers```  instead of the official one  
    0. Run ```etree/k8s-master/setup.sh``` with bash  
    0. ```etree/k8s-master/tools/cifar_division``` and ```etree/k8s-master/tools/mnist_division``` 
    require ```torch, keras, torchvison, cuda, cudnn, etc``` on Master, anaconda3 recommended  
0. On Node
    0. Copy ```/etree``` into Node, or just ```etree/node``` and ```etree/k8s-node```  
    0. Type ```kubeadm config images list```  to list the suitable versions, modify ```etree/k8s-node/setup.sh```, and run it`with bash  
    0. Modify ```etree/node/master_ip.txt```  
0. On Raspberry Pi (if you have, Raspberry Pi OS recommended)  
    0. Change the hostname of your Raspberry Pi follows r1, r2 ...  
    0. Install tensorflow==1.15.0, look https://github.com/PINTO0309/Tensorflow-bin#usage for details  
    0. Copy ```etree/node``` into your Raspberry Pi, no need for the entire ```/etree```, and ```pip3 install -r node/requirements.txt```  
    0. Modify ```etree/node/master_ip.txt```  
### Brief Overview
0. Manually distribute the project files, datasets to Nodes and Raspberry Pi  
0. Master run ```master.py```  
0. Nodes and Raspberry Pi run ```perf_eval.py``` and send results to the Master  
0. Master define the ETree topology and send to Nodes and Raspberry Pi  
0. Nodes and Raspberry Pi run distributed machine learning and send results to the Master  
### Run
0. On Master, modify ```etree/k8s-master/tools/graph_gen.py```, and run with python3  
0. On Master, modify ```etree/k8s-master/tools/env_addr.txt```, look ```etree/k8s-master/tools/README.md``` for details  
0. Prepare datasets  
    0. Divide your data and distribute it to the Nodes and Raspberry Pi  
    0. On Master, modify ```etree/k8s-master/tools/env_datasets.txt``` , and run with python3 to generate incomplete env files, look ```etree/k8s-master/tools/README.md``` for details  
    0. Manually distribute ```etree/k8s-master/env_datasets/*.env```, to corresponding Nodes in folder ```etree/node/env/``` and Raspberry Pi in folder ```node/env/```
0. On Master, run ```etree/k8s-master/master.py``` with python3 and keep this python program running on a terminal (called Ter). It will display massages later  
0. On Master, modify ```--apiserver-advertise-address``` in ```etree/k8s-master/run.sh```, and run with bash  
0. On Node, make sure there exists ```/etc/cni/net.d/*flannel.conf*```, and has the same name and content as the one in Master. You may just copy the file from Master  
0. On Node, make sure there exists ```/run/systemd/resolve/resolv.conf```. It doesn't matter what content is in the file. You may just create an empty file, and it will auto deleted after you shutdown your computer  
0. On Node, turn off swap, and join the K8s network  
0. On Master, run ```etree/k8s-master/tools/conf_yml_gen.py``` with python3  
0. On Master, modify ```spec:template:spec:nodeName``` in each ```etree/k8s-master/dep-*.yml``` to deploy them to the corresponding Node, following the order defined by```etree/k8s-master/tools/env_addr.txt:server_ip```  
0. On Master, modify ```spec:template:spec:volumes:hostPath:path``` in each ```etree/k8s-master/dep-*.yml```  
0. On Master, run ```etree/k8s-master/dep.sh``` with bash  
0. On Raspberry Pi, run ```node/run.sh``` with bash  
0. On Master, when Ter display ```performance collection completed```, you can modify ```etree/k8s-master/tools/env_tree.txt``` to define the ETree  
0. On Master, run ```etree/k8s-master/tools/conf_env_gen.py``` to generate complete env files  
0. On Master, ```curl localhost:9000/conf``` to auto send the complete env files to the corresponding Nodes and Raspberry Pi  
0. The training will auto start  
0. On Master, when Ter display ```log files parsing completed```, you can check the log files in ```etree/k8s-master/log/```  
### Dataset and Network Model
Write```etree/node/nns/`nn_xx.py```, just like ```etree/node/nns/nn_minst.py```, and modify```etree/node/EL.py``` and ```etree/node/perf_eval.py``` to loads your ```nn_xx.py```  
