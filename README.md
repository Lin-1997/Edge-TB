#最新的项目进展
###已完成部分
- Dockerfile
- docker-compose
###待完成部分
- 网络逻辑和各种参数用yml文件传入，而非当前的硬编码
###使用说明
0. 安装docker >= v19.03
0. 安装docker-compose >= v1.25
0. ```bash setup.sh```
0. Wait and have a coffee
0. ```docker-compose -f run.yml -d```
0. ```docker exec test python test.py &```
0. ```curl localhost:8888/test```
