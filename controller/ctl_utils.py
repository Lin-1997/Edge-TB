import json
import os
import subprocess as sp
import time
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from typing import Dict, IO

import requests
from flask import request

from class_node import Net, Emulator, PhysicalNode

executor = ThreadPoolExecutor()


def send_data(method: str, path: str, address: str, port: int = None,
              data: Dict[str, str] = None, files: Dict[str, IO] = None) -> str:
    f"""
    send a request to ``http://{address}{path}`` or ``http://{address}:{port}{path}``.

    :param method: 'GET' or 'POST'.
    :param path: the path in the URL; should start with '/'.
    :param address: ip:port if {port} is None else only ip.
    :param port: only used when {address} is only ip.
    :param data: only used in 'POST'.
    :param files: only used in 'POST'.
    :return: response.text
    """
    if port:
        address += ':' + str(port)
    if method.upper() == 'GET':
        res = requests.get('http://' + address + '/' + path)
        return res.text
    elif method.upper() == 'POST':
        res = requests.post('http://' + address + '/' + path, data=data, files=files)
        return res.text
    else:
        raise Exception('err method ' + method)


def generate_ports(spec, num_ports) -> list:
    if spec['rule'] == 'sequential':
        return list(range(spec['begin'], spec['begin'] + num_ports))
    else:
        raise Exception('Not supported port rule')


# region Controller functions

def restore_nfs():
    """ restore nfs to system settings. """
    cmd = 'sudo exportfs -r'
    sp.Popen(cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait()


def export_nfs(net: Net):
    """ export the path through nfs. """
    for tag in net.nfsClient:
        client = net.nfsClient[tag]
        path = net.nfsPath[tag]
        # export the path.
        cmd = 'sudo exportfs ' + client + ':' + path
        sp.Popen(cmd, shell=True, stdout=sp.DEVNULL, stderr=sp.STDOUT).wait()
        # check result.
        cmd = 'sudo exportfs -v'
        p = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
        msg = p.communicate()[0].decode()
        if not (path in msg and client in msg):
            raise Exception('share ' + path + ' to ' + client + ' failed')


def print_listener(controller):
    """ Register a listener function that prints the message from worker. """

    @controller.app.route('/print', methods=['POST'])
    def route_print():
        """
        this function can listen message from worker/worker_utils.py, send_print ().
        it will print the ${msg}.
        """
        print(request.form['msg'])
        return ''


def clear_nfs_listener(controller):
    """ Register a listener function that restores nfs. """

    @controller.app.route('/clear/nfs', methods=['POST'])
    def route_clear_nfs():
        """
        this function can listen command from user.
        restore nfs to system settings.
        """
        restore_nfs()
        return ''


def docker_tc_listener(controller):
    """ Register a listener function that receives tc result from docker containers. """

    @controller.app.route('/docker/tc', methods=['POST'])
    def route_docker_tc():
        """
        this function can listen message from worker/agent.py, deploy_docker_tc ().
        it will save the result of deploying docker tc settings.
        """
        data = json.loads(request.form['data'])
        number = data['number']
        name = data['name']
        if number == '-1':
            msg = data['msg']
            print('emulated node ' + name + ' tc failed, err:')
            print(msg)
        else:
            print('emulated node ' + name + ' tc succeed')
            controller.tc_lock.acquire()
            controller.tc_number += int(number)
            if controller.tc_number == controller.net.tcLinkNumber:
                print('tc finish')
            controller.tc_lock.release()
        return ''


def send_address_to_emulator_agent(controller):
    """
    send controller's ``{ip:port}`` to emulators.
    this request can be received by worker/agent.py, route_docker_address ().
    """
    for emulator in controller.net.emulator.values():
        print('send_docker_address: send to ' + emulator.name)
        send_data('GET', '/docker/address?address=' + controller.net.address,
                  emulator.ip, controller.agent_port)


def send_docker_tc(controller):
    """
    send the tc settings to emulators.
    this request can be received by worker/agent.py, route_docker_tc ().
    """
    for emulator in controller.net.emulator.values():
        data = {}
        # collect tc settings of each emulated node in this emulator.
        for e in emulator.eNode.values():
            data[e.name] = {
                'NET_NODE_NIC': e.nic,
                'NET_NODE_TC': e.tc,
                'NET_NODE_TC_IP': e.tcIP,
                'NET_NODE_TC_PORT': e.tcPort
            }
        # the agent in emulator will deploy all tc settings of its emulated nodes.
        print('send_docker_tc: send to ' + emulator.name)
        send_data('POST', '/docker/tc', emulator.ip, controller.agent_port,
                  data={'data': json.dumps(data)})


def deploy_dockerfile(controller, images: dict, emulator_images: dict):
    """
    send the Dockerfile and pip requirements.txt to the agents of emulators.
    this request can be received by worker/agent.py, route_docker_build ().

    :param controller: the Controller.
    :param images: a dict mapping image tag to `[path of Dockerfile, path of pip requirements.txt]`.
    :param emulator_images: a dict mapping emulator name to list/set of images to be used.
    """
    tasks = []
    for emulator_name in emulator_images:
        emulator = controller.net.emulator[emulator_name]
        for e_image_tag in emulator_images[emulator_name]:
            tasks.append(executor.submit(deploy_dockerfile_helper, emulator, e_image_tag,
                                         images[e_image_tag]['dockerfile'], images[e_image_tag]['requirements'],
                                         controller.agent_port))
    wait(tasks, return_when=ALL_COMPLETED)


def deploy_dockerfile_helper(emulator: Emulator, tag: str, path1: str, path2: str, agent_port):
    with open(path1, 'r') as f1, open(path2, 'r') as f2:
        print('deploy_dockerfile: send to ' + emulator.name)
        res = send_data('POST', '/docker/build', emulator.ip, agent_port,
                        data={'tag': tag}, files={'Dockerfile': f1, 'dml_req': f2})
        if res == '1':
            print(emulator.name + ' build image succeed')
        else:
            print(emulator.name + ' build image failed')


def deploy_all_yml(controller):
    """
    send the yml files to the agents of emulators.
    this request can be received by worker/agent.py, route_docker_start ().
    """
    tasks = []
    for s in controller.net.emulator.values():
        if s.eNode:
            tasks.append(executor.submit(deploy_yml, s, controller.dirname, controller.agent_port))
    wait(tasks, return_when=ALL_COMPLETED)


def deploy_yml(emulator: Emulator, path: str, agent_port):
    with open(os.path.join(path, emulator.name + '.yml'), 'r') as f:
        print('deploy_all_yml: send to ' + emulator.name)
        send_data('POST', '/docker/start', emulator.ip, agent_port, files={'yml': f})


def docker_controller_listener(controller):
    """
    this function can listen command from user.
    it can control emulated nodes.
    """

    @controller.app.route('/docker/stop', methods=['GET'])
    def route_docker_stop():
        stop_all_docker(controller)
        return ''

    @controller.app.route('/docker/clear', methods=['GET'])
    def route_docker_clear():
        clear_all_docker(controller)
        return ''

    @controller.app.route('/docker/reset', methods=['GET'])
    def route_docker_reset():
        reset_all_docker(controller)
        return ''


def stop_all_docker(controller):
    """
    send a stop message to emulators.
    stop emulated nodes without removing them.
    this request can be received by worker/agent.py, route_docker_stop ().
    """
    tasks = []
    for s in controller.net.emulator.values():
        if s.eNode:
            tasks.append(executor.submit(stop_docker, s.ip, controller.agent_port))
    wait(tasks, return_when=ALL_COMPLETED)


def stop_docker(emulator_ip: str, agent_port):
    send_data('GET', '/docker/stop', emulator_ip, agent_port)


def clear_all_docker(controller):
    """
    send a clear message to emulators.
    stop emulated nodes and remove them.
    this request can be received by worker/agent.py, route_docker_clear ().
    """
    tasks = []
    for s in controller.net.emulator.values():
        if s.eNode:
            tasks.append(executor.submit(clear_docker, s.ip, controller.agent_port))
    wait(tasks, return_when=ALL_COMPLETED)


def clear_docker(emulator_ip: str, agent_port):
    send_data('GET', '/docker/clear', emulator_ip, agent_port)


def reset_all_docker(controller):
    """
    send a reset message to emulators.
    remove emulated nodes, volumes and network bridges.
    this request can be received by worker/agent.py, route_docker_reset ().
    """
    tasks = []
    for s in controller.net.emulator.values():
        if s.eNode:
            tasks.append(executor.submit(reset_docker, s.ip, controller.agent_port))
    wait(tasks, return_when=ALL_COMPLETED)


def reset_docker(emulator_ip: str, agent_port):
    send_data('GET', '/docker/reset', emulator_ip, agent_port)


def send_device_nfs(controller):
    """
    send the nfs settings to physical nodes.
    this request can be received by worker/agent.py, route_device_nfs ().
    """
    tasks = [executor.submit(send_device_nfs_helper, p, controller.net.ip, controller.agent_port)
             for p in controller.net.pNode.values()]
    wait(tasks, return_when=ALL_COMPLETED)


def send_device_nfs_helper(device: PhysicalNode, ip: str, agent_port):
    data = {'ip': ip, 'nfs': device.nfsMount}
    print('send_device_nfs: send to ' + device.name)
    res = send_data('POST', '/device/nfs', device.ip, agent_port,
                    data={'data': json.dumps(data)})
    err = json.loads(res)
    if not err:
        print('device ' + device.name + ' mount nfs succeed')
    else:
        print('device ' + device.name + ' mount nfs failed, err:')
        print(err)


def send_device_tc(controller):
    """
    send the tc settings to physical nodes.
    this request can be received by worker/agent.py, route_device_tc ().
    """
    for p in controller.net.pNode.values():
        if not p.tc:
            print('device ' + p.name + ' tc succeed')
            continue
        data = {
            'NET_NODE_TC': p.tc,
            'NET_NODE_TC_IP': p.tcIP,
            'NET_NODE_TC_PORT': p.tcPort
        }
        print('device_tc_update: send to ' + p.name)
        res = send_data('POST', '/device/tc', p.ip, controller.agent_port,
                        data={'data': json.dumps(data)})
        if res == '1':
            print('device ' + p.name + ' tc succeed')
            controller.tc_lock.acquire()
            controller.tc_number += len(p.tc)
            if controller.tc_number == controller.net.tcLinkNumber:
                print('tc finish')
            controller.tc_lock.release()
        else:
            print('device ' + p.name + ' tc failed, err:')
            print(res)


def send_device_env(controller):
    """
    send the env to physical nodes.
    this request can be received by worker/agent.py, route_device_env ().
    """
    for p in controller.net.pNode.values():
        data = {
            'NET_CTL_ADDRESS': controller.net.address,
            'NET_AGENT_IP': p.ip,
            'NET_NODE_NIC': p.nic,
            'NET_NODE_NAME': p.name,
            'NET_NODE_ENV': p.env,
        }
        print('send_device_env: send to ' + p.name)
        send_data('POST', '/device/env', p.ip, controller.agent_port,
                  data={'data': json.dumps(data)})


def sent_device_req(controller, path: str):
    """
    send the dml_req.txt to physical nodes.
    this request can be received by worker/agent.py, route_device_req ().
    """
    tasks = [executor.submit(sent_device_req_helper, p, path, controller.agent_port)
             for p in controller.net.pNode.values()]
    wait(tasks, return_when=ALL_COMPLETED)


def sent_device_req_helper(device: PhysicalNode, path: str, agent_port):
    with open(path, 'r') as f:
        print('sent_device_req: send to ' + device.name)
        res = send_data('POST', '/device/req', device.ip, agent_port,
                        files={'dml_req': f})
        if res == '1':
            print('device ' + device.name + ' req succeed')
        else:
            print('device ' + device.name + ' req failed, err:')
            print(res)


def deploy_all_device(controller):
    """
    send a start message to physical nodes.
    this request can be received by worker/agent.py, route_device_start ().
    """
    tasks = [executor.submit(deploy_device, p, controller.agent_port)
             for p in controller.net.pNode.values()]
    wait(tasks, return_when=ALL_COMPLETED)


def deploy_device(device: PhysicalNode, agent_port):
    data = {'dir': device.workingDir, 'cmd': device.cmd}
    send_data('POST', '/device/start', device.ip, agent_port,
              data={'data': json.dumps(data)})


def device_controller_listener(controller):
    """
    this function can listen command from user.
    it can controller physical nodes.
    """

    @controller.app.route('/device/stop', methods=['GET'])
    def route_device_stop():
        stop_all_device(controller)
        return ''

    @controller.app.route('/device/clear/tc', methods=['GET'])
    def route_device_clear_tc():
        clear_all_device_tc(controller)
        return ''

    @controller.app.route('/device/clear/nfs', methods=['GET'])
    def route_device_clear_nfs():
        clear_all_device_nfs(controller)
        return ''

    @controller.app.route('/device/reset', methods=['GET'])
    def route_device_reset():
        reset_all_device(controller)
        return ''


def stop_all_device(controller):
    """
    send a stop message to physical nodes.
    kill the process started by above deploy_device ().
    this request can be received by worker/agent.py, route_device_stop ().
    """
    tasks = [executor.submit(stop_device, p.ip, controller.agent_port)
             for p in controller.net.pNode.values()]
    wait(tasks, return_when=ALL_COMPLETED)


def stop_device(device_ip: str, agent_port):
    send_data('GET', '/device/stop', device_ip, agent_port)


def clear_all_device_tc(controller):
    """
    send a clear tc message to physical nodes.
    clear all tc settings.
    this request can be received by worker/agent.py, route_device_clear_tc ().
    """
    tasks = [executor.submit(clear_device_tc, p.ip, controller.agent_port)
             for p in controller.net.pNode.values()]
    wait(tasks, return_when=ALL_COMPLETED)


def clear_device_tc(device_ip: str, agent_port):
    send_data('GET', '/device/clear/tc', device_ip, agent_port)


def clear_all_device_nfs(controller):
    """
    send a clear nfs message to physical nodes.
    unmount all nfs.
    this request can be received by worker/agent.py, route_device_clear_nfs ().
    """
    tasks = [executor.submit(clear_device_nfs, p.ip, controller.agent_port)
             for p in controller.net.pNode.values()]
    wait(tasks, return_when=ALL_COMPLETED)


def clear_device_nfs(device_ip: str, agent_port):
    send_data('GET', '/device/clear/nfs', device_ip, agent_port)


def reset_all_device(controller):
    """
    send a reset message to physical nodes.
    kill the process started by above deploy_device ().
    clear all tc settings.
    unmount all nfs.
    this request can be received by worker/agent.py, route_device_reset ().
    """
    tasks = [executor.submit(reset_device, p.ip, controller.agent_port)
             for p in controller.net.pNode.values()]
    wait(tasks, return_when=ALL_COMPLETED)


def reset_device(device_ip: str, agent_port):
    send_data('GET', '/device/reset', device_ip, agent_port)


def update_tc_listener(controller):
    @controller.app.route('/update/tc', methods=['GET'])
    def route_update_tc():
        """
        this function can listen command from user.
        it can update the tc settings of emulated and/or physical nodes.
        """
        print('update tc start at ' + str(time.time()))
        filename = request.args.get('file')
        if filename[0] != '/':
            filename = os.path.join(controller.dirname, filename)

        with open(filename, 'r') as f:
            all_nodes = []
            emulator_to_node = {}  # emulator to emulated nodes in this emulator.
            links_json = json.loads(f.read().replace('\'', '\"'))
            for name in links_json:
                n = controller.net.get_node_by_name(name)
                all_nodes.append(n)
                n.tc.clear()
                n.tcIP.clear()
                n.tcPort.clear()
            controller.net.load_bw(links_json)
            for node in all_nodes:
                if node.name in controller.net.pNode:
                    executor.submit(update_device_tc, node, controller.agent_port)
                else:
                    emulator = node.emulator
                    emulator_to_node.setdefault(emulator, []).append(node)
            update_docker_tc(emulator_to_node, controller.agent_port)
        return ''


def update_device_tc(device, agent_port):
    data = {
        'NET_NODE_TC': device.tc,
        'NET_NODE_TC_IP': device.tcIP,
        'NET_NODE_TC_PORT': device.tcPort
    }
    print('update_device_tc: send to ' + device.name)
    res = send_data('POST', '/device/tc/update', device.ip, agent_port,
                    data={'data': json.dumps(data)})
    print(device.name + ' update tc end at ' + str(time.time()))
    if res == '1':
        print('physical node ' + device.name + ' update tc succeed')
    else:
        print('physical node ' + device.name + ' update tc failed, err:')
        print(res)


def update_docker_tc(emulator_to_node, agent_port):
    for emulator in emulator_to_node:
        data = {}
        for e in emulator_to_node[emulator]:
            data[e.name] = {
                'NET_NODE_NIC': e.nic,
                'NET_NODE_TC': e.tc,
                'NET_NODE_TC_IP': e.tcIP,
                'NET_NODE_TC_PORT': e.tcPort
            }
        executor.submit(update_docker_tc_helper, data, emulator, agent_port)


def update_docker_tc_helper(data, emulator, agent_port):
    print('update_docker_tc: send to ' + emulator.name)
    res = send_data('POST', '/docker/tc/update', emulator.ip, agent_port,
                    data={'data': json.dumps(data)})
    print(emulator.name + ' update tc end at ' + str(time.time()))
    ret = json.loads(res)
    for name in ret:
        if ret[name]['number'] == '-1':
            print('emulated node ' + emulator.name + ': ' + name + ' update tc failed, err:')
            print(ret[name]['msg'])
        else:
            print('emulated node ' + emulator.name + ': ' + name + ' update tc succeed')

# endregion
