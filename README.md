#最新的项目进展
###以完成部分
- 将worker和aggregator的功能合并在了hybrid
- 在hybrid中以硬编码的方式定义了一个测试用的网络逻辑
- 已测试，EL中所有功能均通过
###待完成部分
- 实现docker-compose方式启动
- 网络逻辑和各种参数用yml文件传入，而非当前的硬编码
###使用说明
0. pip install -r requirements.txt
0. 对于GL python gossip_test.py
0. 对于EL python start.py
0. 若要自定义EL网络，请修改Hybrid.py中相应部分（并不推荐
0. 若要测试FL，请修改Hybrid.py中相应部分（然而也不推荐
