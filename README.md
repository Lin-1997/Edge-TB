# 最新的项目进展
### 已完成部分
- Dockerfile
- docker-compose
- ContainerNet
### 待完成部分
- ??
### 安装说明
0. Linux required
0. Install docker >= v19.03
0. Install docker-compose >= v1.25 (docker-compose启动，仅测试代码，不能指定节点资源，网络资源)   
0. Bare-metal install Containernet >= master branch 7ad907e (ContainerNet启动，Testbed，能指定节点资源，网络资源，推荐使用)
0. ```sudo bash setup.sh```
0. Wait and have a coffee
### docker-compose启动说明
0. 如果要自定义网络
    0. 定义一个N个节点的网络，比如4
    0. ```python3 generate_yml.py -n 4```
    0. 在./env中编写1.env~n.env，格式说明参见./env/README.md
    0. 务必将节点1作为最上层的节点
0. ```docker-compose -f run.yml &```
0. 等到显示N个Serving Flask app "hybrid" (lazy loading)
0. EL->```curl localhost:8888/start```
0. FL->```curl localhost:8888/start?layer=0```
0. 显示training ended后可在.log/查看训练情况
### Containernet启动说明
0. 如果要自定义网络
    0. 修改containernet.py
    0. 在./env中编写1.env~n.env，格式说明参见./env/README.md
    0. 务必将节点1作为最上层的节点
0. ```sudo python3 containernet.py``` 
0. EL->换一个控制台```curl localhost:8888/start```
0. FL->换一个控制台```curl localhost:8888/start?layer=0```
0. (在containernet中 print() 不会显示出来，不知道什么时候才算训练完)，自己看.log/查看训练情况
### 关于数据集
如果要用minst或者cifar数据集，请自行下载到etree目录下，然后修改nn/nn_minst或者nn/nn_cifar中涉及到数据集地址的代码，留意不要把数据集commit到git上
### 物理网络拓扑图信息
详情可参考`./graph/README.md`