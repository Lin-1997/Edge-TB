#最新的项目进展
###已完成部分
- Dockerfile
- docker-compose
###待完成部分
- 集成到ContainerNet
###安装说明
0. Install docker >= v19.03
0. Install docker-compose >= v1.25
0. ```bash setup.sh```
0. Wait and have a coffee
###使用说明
0. 如果要自定义网络
    0. 定义一个N个节点的网络，比如4
    0. ```python3 generate_yml.py -n 4```
    0. 在./env中编写0.env~n-1.env，格式说明参见./env/README.md
    0. 务必将节点0作为最上层的节点
0. ```docker-compose -f run.yml &```
0. 等到显示N个Serving Flask app "hybrid" (lazy loading)
0. ```curl localhost:8888/start```
0. 显示training ended后可在.log/查看训练情况
