# 最新的项目进展
### 已完成部分
- Dockerfile
- K8s
### 待完成部分
- 模拟网速限制
### 安装说明
0. At least 2 computers, each with 2-cores and 2G memory, one acts as master and one acts as node
0. Linux required, Ubuntu 18.04 LTS recommend
0. Install K8s and docker, see https://www.jianshu.com/p/f2d4dd4d1fb1
0. On master
    0. ```sudo bash ./master/setup.sh```
0. On node
    0. ```sudo bash ./setup.sh```
    0. ```sudo bash ./node/setup.sh```
### 启动说明
0. 如果要自定义一个N个节点的网络
    0. On master, 修改的./master/etree.yml
    0. On node, 在./env中编写n1.env~nN.env，格式说明参见./env/README.md
0. 在master中 ```bash ./master/run.sh```
0. 在node中，加入K8s网络
0. 在master中，```bash ./master/deployment.sh```
0. 假设n1为最顶层的节点
0. 启动EL->在master中，进入n1的容器 ```curl http://n1的地址/start```
0. 启动FL->在master中，进入n1的容器 ```curl http://n1的地址/start?layer=0```
0. 似乎不会输出任何东西，不知道什么时候才算训练完，自己去node中的./log查看训练情况，或者 ```docker logs $(容器名)``` 查看容器输出
### 关于数据集
如果要用minst或者cifar数据集，请自行下载到etree目录下，修改nns/nn_minst或者nns/nn_cifar中涉及到数据集地址的代码，修改hybrid.py中调用nns的代码。注意不要把数据集commit到git上
### 关于网络模型
如果要自定义网络模型，准备好数据集后，在nns/中编写nn_xx.py，格式参见现有的代码，暴露出必要的api，修改hybird.py中调用nns的代码。注意自定义的网络模型以及相应的数据集也不要commit到git上
### 物理网络拓扑图信息
详情可参考`./graph/README.md`
