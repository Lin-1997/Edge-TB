import os
from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel

setLogLevel ('info')
from_path = os.path.abspath (os.path.dirname (__file__))
to_path = ':/home/ETree'

net = Containernet (controller=Controller)
info ('*** Adding controller\n')
net.addController ('c0')
info ('*** Adding docker containers\n')
n1 = net.addDocker ('n1', ip='10.0.0.1', dimage="etree", dcmd="python hybrid.py",
	volumes=[from_path + to_path], ports=[8888], port_bindings={8888: 8888})
n2 = net.addDocker ('n2', ip='10.0.0.2', dimage="etree", dcmd="python hybrid.py",
	volumes=[from_path + to_path])
n3 = net.addDocker ('n3', ip='10.0.0.3', dimage="etree", dcmd="python hybrid.py",
	volumes=[from_path + to_path])
n4 = net.addDocker ('n4', ip='10.0.0.4', dimage="etree", dcmd="python hybrid.py",
	volumes=[from_path + to_path])
info ('*** Adding switches\n')
s1 = net.addSwitch ('s1')
# s2 = net.addSwitch ('s2')
info ('*** Creating links\n')
net.addLink (n1, s1)
net.addLink (n2, s1)
net.addLink (n3, s1)
net.addLink (n4, s1)
# net.addLink (s1, s2, cls=TCLink, delay='100ms', bw=1)
# net.addLink (s2, n2)
info ('*** Starting network\n')
net.start ()
info ('*** Testing connectivity\n')
net.ping ([n1, n2])
net.ping ([n1, n3])
net.ping ([n1, n4])
info ('*** Running CLI\n')
CLI (net)
info ('*** Stopping network')
net.stop ()
