import os
import random

from flask import Flask

import ctl_utils
import ra_manager
from class_node import Net

if __name__ == '__main__':
    dirname = os.path.abspath(os.path.dirname(__file__))
    ip = '192.168.2.25'
    port = 3333
    net = Net(ip, port)
    net.add_nfs(tag='dml_app', ip='192.168.2.0', mask=24,
                path=os.path.join(dirname, 'dml_app'))
    net.add_nfs(tag='dataset', ip='192.168.2.0', mask=24,
                path=os.path.join(dirname, 'dataset'))
    ctl_utils.restore_nfs()
    ctl_utils.export_nfs(net)

    dml_port = 4444

    nList = []
    nDict = {}

    start_index = 1
    emu1 = net.add_emulator('3990x', '192.168.2.4')
    emu1.mount_nfs('dml_app')
    emu1.mount_nfs('dataset')
    for i in range(8):
        nList.append(emu1.add_node(f'n{i + start_index}', 'eth0', '/home/worker/dml_app',
                                   ['python3', 'ra_peer.py'], 'dml:v1.0', cpu=2, memory=2, unit='G'))
        nDict['n' + str(i + start_index)] = []
        nList[-1].add_volume('./dml_file', '/home/worker/dml_file')
        nList[-1].add_nfs('dml_app', '/home/worker/dml_app')
        nList[-1].add_nfs('dataset', '/home/worker/dataset')
        nList[-1].add_port(dml_port, 8000 + i + start_index)

    net.save_node_ip()

    node_names = list(nDict.keys())
    node_count = len(node_names)
    for i in range(8):
        left = (i + node_count - 1) % node_count
        net.asymmetrical_link(nList[i], nList[left], bw=random.randint(200, 500), unit='kbps')

    net.save_bw()

    # links_json = ctl_utils.read_json (os.path.join (dirname, 'links.json'))
    # net.load_bw (links_json)

    net.save_yml()

    app = Flask(__name__)

    ctl_utils.print_listener(app)

    ctl_utils.docker_tc_listener(app, net)
    ctl_utils.send_docker_address(net)
    # path_dockerfile = os.path.join (dirname, 'dml_app/Dockerfile')
    # path_req = os.path.join (dirname, 'dml_app/dml_req.txt')
    # ctl_utils.deploy_dockerfile (net, 'dml:v1.0', path_dockerfile, path_req)

    ctl_utils.send_device_nfs(net)
    ctl_utils.send_device_env(net)
    # path_req = os.path.join (dirname, 'dml_app/dml_req.txt')
    # ctl_utils.sent_device_req (net, path_req)

    if net.tcLinkNumber > 0:
        ctl_utils.send_docker_tc(net)
        ctl_utils.send_device_tc(net)
    else:
        print('tc finish')

    ctl_utils.update_tc_listener(app, net)

    ctl_utils.docker_controller_listener(app, net)
    ctl_utils.device_controller_listener(app, net)
    ctl_utils.clear_nfs_listener(app)

    ra_manager.manager(app, net)

    ctl_utils.deploy_all_device(net)
    ctl_utils.deploy_all_yml(net)

    app.run(host='0.0.0.0', port=port, threaded=True)
