#最新的项目进展
###已完成部分
- Dockerfile
- docker-compose
- ContainerNet
###待完成部分
- 全连接裁剪 成init网络 CPU 内存
- init网络输入he.py，输入gan.py 输出.env
containernet.py load .env = done
###安装说明
0. Install docker >= v19.03
0. Install docker-compose >= v1.25 (docker-compose启动)
0. Bare-metal install Containernet >= master branch 7ad907e (ContainerNet启动)
0. ```bash setup.sh```
0. Wait and have a coffee
###docker-compose启动说明
0. 如果要自定义网络
    0. 定义一个N个节点的网络，比如4
    0. ```python3 generate_yml.py -n 4```
    0. 在./env中编写1.env~n.env，格式说明参见./env/README.md
    0. 务必将节点1作为最上层的节点
0. ```docker-compose -f run.yml &```
0. 等到显示N个Serving Flask app "hybrid" (lazy loading)
0. ```curl localhost:8888/start```
0. 显示training ended后可在.log/查看训练情况
###Containernet启动说明
0. 如果要自定义网络
    0. 修改containernet.py
    0. 在./env中编写1.env~n.env，格式说明参见./env/README.md
    0. 务必将节点1作为最上层的节点
0. ```sudo python3 containernet.py``` 
0. 换一个控制台```curl localhost:8888/start```
0. (这东西似乎没有任何输出，不知道什么时候才算训练完)，自己看.log/查看训练情况
