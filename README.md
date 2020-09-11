### Installation
0. At least 2 computers, each with 2-cores and 2G memory, one acts as Master and others act as Nodes  
0. Linux required, Ubuntu recommended  
0. Install python3 and python3-pip  
0. Install K8s and Docker. For Chinese users, look https://www.jianshu.com/p/f2d4dd4d1fb1 for details  
0. Install NFS. For Chinese users, look https://blog.csdn.net/networken/article/details/105997728 for details  
0. On Master  
    0. Type ```kubeadm config images list```  to list the suitable versions, and modify ```etree/k8s-master/setup.sh```  
    0. The docker image can be obtained through the official registry  
    0. For Chinese users, it may be better to use ```registry.aliyuncs.com/google_containers```  instead of the official one  
    0. Run ```etree/k8s-master/setup.sh``` with bash. This command will install numpy and matplotlib through pip3, take carefully
0. On Node, Similar to Master-setup, and run ```etree/k8s-node/setup.sh``` with bash  
0. On Raspberry Pi (if you have, Raspberry Pi OS recommended)  
    0. Change the hostname of your Raspberry Pi follows r1, r2 ...  
    0. Install tensorflow==1.15.0, look https://github.com/PINTO0309/Tensorflow-bin#usage for details  
    0. Copy ```etree/node``` into your Raspberry Pi, no need for the entire ```/etree```, and ```pip3 install -r node/requirements.txt```  
### Run
0. On Master, modify ```etree/tools/graph_gen.py```, and run with python3  
0. On Master, modify ```etree/tools/env.txt```, look ```etree/tools/README.md``` for details  
0. On Master, run ```etree/tools/conf_gen.py``` with python3  
0. On Master, export ```/abs/path/to/etree/node``` through NFS, don't export the entire ```/etree```  
0. On Master, modify ```spec:nfs:path``` and ```spec:nfs:server``` in ```etree/k8s-master/nfs.yml```  
0. On Master, modify ```--apiserver-advertise-address``` in ```etree/k8s-master/run.sh```, and run with bash  
0. On Node, make sure there exists ```/etc/cni/net.d/*flannel.conf*```, and has the same name and content as the one in Master 
0. On Node, make sure there exists ```/run/systemd/resolve/resolv.conf```. It doesn't matter what content is in the file  
0. On Node, turn off swap, and join the K8s network  
0. On Raspberry Pi (if you have), copy ```r*.env``` from Master ```etree/node/env``` to the corresponding Raspberry Pi, and run ```node/node.py``` with python3  
0. On Master, modify ```etree/k8s-master/dep.sh``` to deploy each ```dep.yml``` in one Node, and run ```etree/k8s-master/dep.sh``` with bash  
0. Suppose n1 is the top-layer aggregator in etree  
0. To start EL->On Master, ```curl http://n1's address/start```  
0. To start FL->On Master, ```curl http://n1's address/start?layer=0```  
0. On Master, ```cat etree/node/log/n*.log```, or ```docker logs $(container ID)```   
0. For Raspberry Pi (if you have), ```cat node/log/r*.log```  
### Dataset and Network model
Write```etree/node/nns/`nn_xx.py```, expose API just like ```etree/node/nns/nn_minst.py```, and modify```etree/node/node.py``` to loads your ```nn_xx.py```  
