
# Testing the codes in topograph.py
from mininet.cli import CLI
from mininet.net import Containernet
from mininet.node import Controller

from graph.topograph import TopoGraph, random_graph, generate_ip_for_hosts
from graph import TYPE_HOST, TYPE_SW


def mn_test(topo_g, docker_info_tmp):
    net = Containernet(controller=Controller)
    net.addController("c0")
    name2ip = generate_ip_for_hosts(topo_g.get_host_names())
    topo_g.build(net, name2ip, docker_info_tmp)
    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    g = TopoGraph()
    docker_info = {"dimage": "ubuntu:trusty"}
    g.add_node('n1', TYPE_HOST, docker_info)
    g.add_node('n2', TYPE_HOST, docker_info)
    g.add_node('s1', TYPE_SW)
    g.connect('n1', 's1', None)
    g.connect('n2', 's1', None)
    json_str = g.to_json()
    g_tmp = TopoGraph()
    g_tmp.from_json(json_str)
    print("g_tmp")
    print(g_tmp.to_json())
    print(g_tmp.route_path('n1', 'n2'))
    rg, host_names = random_graph(10, 6)
    print(rg.to_json())
    print(rg.route_path(host_names[0], host_names[3]))
    print(generate_ip_for_hosts(host_names))
    mn_test(rg, docker_info)
