# API for topograph.py
## 获得拓扑图的两种方式
1. 使用random_graph，传入host的数量、所希望的switch的数量以及一些其他相关docker参数（除cpu和memory）（以python dict的形式传入）
```
{'dimage': 'ubuntu:trusty'}
```
    - random_graph返回两个值，第一个是TopoGraph，第二个是所有host的名称的列表
2. 自建立TopoGraph
```
    g = TopoGraph()
    # docker_info中的信息是可选的信息字段， dimage是必备的，其他可参考 https://github.com/containernet/containernet/wiki/APIs
    docker_info = {"dimage": "ubuntu:trusty", "cpu_weight": 1, "mem_limit": "2G"} 
    g.add_node('n1', TYPE_HOST, docker_info)
    g.add_node('n2', TYPE_HOST, docker_info)
    g.add_node('s1', TYPE_SW)
    g.connect('n1', 's1', {"delay": "0ms", "bw": 1.0})  # bw是带宽，单位为Mbps； delay是链路延迟，需要自带单位（如ms）
    g.connect('n2', 's1', None)
```
## 把拓扑图保存下来
- 以上述例子中的`g`为例，`g.to_json()`可以把TopoGraph转换成json格式的字符串并保存到文件
- 若需要读取已保存的json格式的TopoGraph，假设`g_json`是json格式的TopoGraph，那么可以使用以下代码读取：
```
    g_tmp = TopoGraph()
    g_tmp.from_json(g_json)
```
## 获取拓扑图中的host名字
以上述例子中的`g`为例，`g.get_host_names()`可以获取其host的名称列表
## 使用TopoGraph建立仿真网络
以上述例子中的`g`为例
1. `host_names = g.get_host_names()`
2. `name_to_ip = generate_ip_for_hosts(host_names)` 该函数可以生成host name到ip的映射，ip从`10.0.0.1`开始生成；也可以选择自行以python dict的形式建立host name到ip的映射。
3. 
```
    net = Containernet(controller=Controller)
    net.addController("c0")
    g.build(net, name_to_ip)
    net.start()  # 启动仿真网络
    CLI(net)  # 进入仿真网络的操作命令行
    net.stop()  # 停止仿真网络
```