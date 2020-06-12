# 最新的项目进展
### 已完成部分
- Dockerfile
- Containernet
### 待完成部分
- ??
### 安装说明
0. Linux required
0. Install docker >= v19.03
0. Bare-metal install Containernet >= master branch 7ad907e
0. ```sudo bash setup.sh```
0. Wait and have a coffee
### 启动说明
0. 如果要自定义一个N个节点的网络
    0. 修改containernet.py
    0. 在./env中编写n1.env~nN.env，格式说明参见./env/README.md
0. ```sudo python3 containernet.py```
0. 假设n1为最顶层的节点
0. 启动EL->在containernet中 ```n1 curl n1:8888/start```
0. 启动FL->在containernet中 ```n1 curl n1:8888/start?layer=0```
0. 在containernet中似乎不会输出任何东西，不知道什么时候才算训练完，自己去./log查看训练情况，或者 ```docker logs $(容器名)``` 查看容器输出
### 关于数据集
如果要用minst或者cifar数据集，请自行下载到etree目录下，修改nn/nn_minst或者nn/nn_cifar中涉及到数据集地址的代码，修改hybrid.py中调用nn的代码。注意不要把数据集commit到git上
### 关于网络模型
如果要自定义网络模型，准备好数据集后，在nn/中编写nn_xx.py，格式参见现有的代码，暴露出必要的api，修改hybird.py中调用nn的代码。注意自定义的网络模型以及相应的数据集也不要commit到git上
### 物理网络拓扑图信息
详情可参考`./graph/README.md`
