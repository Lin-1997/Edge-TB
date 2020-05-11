
# Testing the codes in topograph.py
from mininet.cli import CLI
from mininet.net import Containernet
from mininet.node import Controller

from graph.topograph import TopoGraph
from graph import TYPE_HOST, TYPE_SW


def mn_test(topo_g):
    net = Containernet(controller=Controller)
    net.addController("c0")
    name2ip = {"n1": "10.0.0.1", "n2": "10.0.0.2"}
    docker_info = {"dimage": "ubuntu:trusty"}
    topo_g.build(net, name2ip, docker_info)
    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    g = TopoGraph()
    g.connect('n1', TYPE_HOST, 's1', TYPE_SW, None)
    g.connect('n2', TYPE_HOST, 's1', TYPE_SW, None)
    json_str = g.to_json()
    g_tmp = TopoGraph()
    g_tmp.from_json(json_str)
    print("g_tmp")
    print(g_tmp.to_json())
    mn_test(g)
