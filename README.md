# 最新的项目进展
### 已完成部分
- Dockerfile
- K8s
### 待完成部分
- NFS
### 安装说明
0. At least 2 computers, each with 2-cores and 2G memory, one acts as master and others act as nodes
0. Linux required, Ubuntu 18.04 LTS recommend
0. Install K8s and docker, see https://www.jianshu.com/p/f2d4dd4d1fb1
0. On master
    0. ```sudo bash ./master/setup.sh```
0. On node
    0. ```sudo bash ./setup.sh```
    0. ```sudo bash ./node/setup.sh```
### 启动说明
0. On master, ```python3 ./env/graph_gen.py -n -p -b -t```  
    -n，节点数量；-p，0~1，节点间多大概率相互连接；-b，连接的带宽下限，-t，连接的带宽上限，单位是MB/s。最终输出np_graph.txt即网络拓扑图  
0. On master, 编写./env/env.txt，详情可参考```./env/README.md```  
0. On master, ```python3 ./env/conf_gen.py```  
0. 在master中 ```bash ./master/run.sh```  
0. 在node中，关闭swap，加入K8s网络  
0. 在master中，修改```./master/dep.sh```，使得一个dep固定部署到一台node主机上，然后```bash ./master/dep.sh```  
0. 假设n1为最顶层的节点  
0. 启动EL->在master中，进入n1的容器， ```curl http://n1的地址/start```  
0. 启动FL->在master中，进入n1的容器， ```curl http://n1的地址/start?layer=0```  
0. 在node中，```./log```查看训练情况，或者 ```docker logs $(容器名)``` 查看容器输出  
### 关于数据集
如果要用minst或者cifar数据集，请自行下载到etree目录下，修改```./nns/nn_minst```或者```./nns/nn_cifar```中涉及到数据集地址的代码，修改```./hybrid.py```中调用nns的代码。注意不要把数据集commit到git上
### 关于网络模型
如果要自定义网络模型，准备好数据集后，编写```./nns/`nn_xx.py```，格式参见现有的代码，暴露出必要的api，修改```./hybird.py```中调用nns的代码。注意自定义的网络模型以及相应的数据集也不要commit到git上
### ~~物理网络拓扑图信息~~ K8s中已弃用
详情可参考`./graph/README.md`
