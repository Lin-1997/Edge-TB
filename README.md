# 最新的项目进展
### 已完成部分
- Dockerfile
- K8s
- NFS
### 安装说明
0. At least 2 computers, each with 2-cores and 2G memory, one acts as master and others act as nodes
0. Linux required
0. Install K8s and docker and , see https://www.jianshu.com/p/f2d4dd4d1fb1
0. Install NFS, see https://blog.csdn.net/networken/article/details/105997728
0. On master
    0. ```sudo bash etree/k8s/master_setup.sh```
0. On node
    0. ```sudo bash etree/setup.sh```
    0. ```sudo bash etree/k8s/node_setup.sh```
### 启动说明
0. 在master中，修改```etree/tools/graph_gen.py```，然后python3运行  
0. 在master中，修改```etree/tools/env.txt```，参考```etree/tools/README.md```  
0. 在master中，python3运行```etree/tools/conf_gen.py```  
0. 在master中，bash运行 ```etree/k8s/run.sh```  
0. 在node中，关闭swap，加入K8s网络  
0. 在master中，修改```etree/k8s/dep.sh```，使得一个dep.yml固定部署到一台node主机上，然后bash运行``` etree/k8s/dep.sh```  
0. 假设n1为最顶层的节点  
0. 启动EL->在master中，进入n1的容器， ```curl http://n1的地址/start```  
0. 启动FL->在master中，进入n1的容器， ```curl http://n1的地址/start?layer=0```  
0. 在master中，```etree/node/log```查看训练情况，或者在node中，```docker logs $(容器名)``` 查看容器输出  
### 关于数据集
如果要用minst或者cifar数据集，请自行下载到etree目录下，修改```etree/node/nns/nn_minst```或者```etree/node/nns/nn_cifar```中涉及到数据集地址的代码，修改```etree/node/node.py```中调用nns的代码。注意不要把数据集commit到git上
### 关于网络模型
如果要自定义网络模型，准备好数据集后，编写```etree/node/nns/`nn_xx.py```，格式参见现有的代码，暴露出必要的api，修改```etree/node/node.py```中调用nns的代码。注意自定义的网络模型以及相应的数据集也不要commit到git上
### ~~物理网络拓扑图信息~~ 已弃用，使用tools内工具
详情可参考`etree/graph/README.md`
