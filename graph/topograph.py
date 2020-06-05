import random
import uuid
import json
from collections import deque

from graph import *


def get_info(ele):
    if isinstance(ele, Node):
        if ele.type == TYPE_SW:
            return json.dumps({})
        else:
            return json.dumps(get_host_info(ele))
    elif isinstance(ele, Edge):
        return json.dumps(get_link_info(ele))
    else:
        return json.dumps({})


def get_host_info(host_node):
    node_info = {'name': host_node.name}
    if host_node.type == TYPE_HOST:
        node_info['type'] = 'host'
        node_info['cpu'] = host_node.get_cpu_limit()
        node_info['memory'] = host_node.get_mem_limit()
    elif host_node.type == TYPE_SW:
        node_info['type'] = 'switch'
    else:
        node_info['type'] = 'unknown'
    return node_info


def get_link_info(link_edge):
    edge_info = {'edge_id': link_edge.edge_id, 'delay': link_edge.get_delay(), 'bw': link_edge.get_bw()}
    return edge_info


class TopoGraph(JSONable):
    def __init__(self):
        self._node_list = {}
        self._docker_host_list = {}
        self._cpu_percentage_is_set = False

    def add_node(self, name, node_type, docker_info=None):
        if name not in self._node_list:
            if node_type == TYPE_HOST:
                self._cpu_percentage_is_set = False
                self._node_list[name] = Node(name, node_type, docker_info)
                self._docker_host_list[name] = self._node_list[name]
            else:
                self._node_list[name] = Node(name, node_type, None)

    def connect(self, src_name, dst_name, link_attributes):
        if src_name in self._node_list and dst_name in self._node_list:
            src_node = self._node_list.get(src_name)
            dst_node = self._node_list.get(dst_name)
            link = Edge(src_name, dst_name, link_attributes)
            src_node.add_neighbor(link)
            dst_node.add_neighbor(link)
        else:
            # log error
            pass

    def route_path(self, src_node_name, dst_node_name):
        """
        Query the route path from src_node_name to dst_node_name.
        :param src_node_name: the name of the source node.
        :param dst_node_name: the name of the destination node.
        :return: a JSON array string, the sequence in the array is the sequence of the links and nodes in the path.
        """
        if not self._cpu_percentage_is_set:  # In case that the cpu percentage is not precise.
            self.cal_cpu_percentage()

        if src_node_name not in self._node_list:
            # log error
            return []
        if dst_node_name not in self._node_list:
            # log error
            return []
        src_node = self._node_list.get(src_node_name)
        # BFS to find the shortest path
        visited = {src_node_name}
        queue = deque([(src_node_name, src_node.get_neighbors())])
        tree = {}
        while queue:
            parent, children = queue.pop()
            next_children = []
            for child_name in children:
                if child_name not in visited:
                    next_children.append(child_name)
                    visited.add(child_name)
                    queue.append((child_name, self._node_list[child_name].get_neighbors()))
            if next_children:
                tree[parent] = next_children

        # DFS to find the best way
        # Prune the path cannot reach `dsts`
        def dfs(bfs_tree, cur, dsts_dfs):
            cur_sw_list = bfs_tree.get(cur, [])
            if not cur_sw_list:
                # This means that the switch is the end of the path
                if cur not in dsts_dfs:
                    return False
                else:
                    return True
            else:
                item_to_remove = []
                for next_sw in cur_sw_list:
                    good_path = dfs(bfs_tree, next_sw, dsts_dfs)
                    if not good_path:
                        item_to_remove.append(next_sw)
                # Remove the item needed to be removed
                for item in item_to_remove:
                    bfs_tree.get(cur).remove(item)
                if not bfs_tree.get(cur, []):
                    # Bug fixed
                    bfs_tree.pop(cur)
                    # Bug fixed: When the destination is the leaf node, it cannot recognize the path.
                    if cur in dsts_dfs:
                        return True
                    else:
                        return False
                else:
                    return True

        pruned_tree = tree.copy()
        dfs(pruned_tree, src_node_name, [dst_node_name])

        # Fill the route_path with the information of nodes and links
        route_path = []
        cur_name = src_node_name
        route_path.append(self._node_list[cur_name])
        while cur_name in pruned_tree:
            next_name = pruned_tree[cur_name][0]
            route_path.append(self._node_list[cur_name].get_edge_by_neighbor(next_name))
            route_path.append(self._node_list[next_name])
            cur_name = next_name

        # Change route_path to json string list.
        return [get_info(ele) for ele in route_path]

    def to_json(self):
        json_obj = self._node_list.copy()
        for key, value in json_obj.items():
            json_obj[key] = value.to_json()
        return json.dumps(json_obj)

    def from_json(self, json_str):
        json_obj = json.loads(json_str)
        for key, value in json_obj.items():
            node = Node()
            node.from_json(value)
            self._node_list[key] = node
            if node.type == TYPE_HOST:
                self._docker_host_list[key] = node

    def build(self, net, name2ip):
        """
        Build the mininet according to the topology graph
        :param net: the object of mininet
        :param name2ip: the mapping of node name and ip (except the switches)
        :return:
        """
        net_nodes = self.build_nodes(net, name2ip)
        self.build_edges(net, net_nodes)

    def build_nodes(self, net, name2ip):
        net_node_list = {}
        if not self._cpu_percentage_is_set:
            self.cal_cpu_percentage()

        for node_name, node in self._node_list.items():
            if node.type == TYPE_HOST:
                host = net.addDocker(node_name, ip=name2ip[node_name], **node.docker_info)
                net_node_list[node_name] = host
            elif node.type == TYPE_SW:
                sw = net.addSwitch(node_name)
                net_node_list[node_name] = sw
            else:
                # log error
                pass
        return net_node_list

    def build_edges(self, net, node_name2node):
        for node in self._node_list.values():
            for edge in node.edges.values():
                src = edge.src_node_name
                dst = edge.dst_node_name
                if src == node.name:  # Only when the edge is started from `node`, the edge will be added to net.
                    src_node = node_name2node[src]
                    dst_node = node_name2node[dst]
                    net.addLink(src_node, dst_node, **edge.link_attributes)

    def cal_cpu_percentage(self):
        weight_sum = 0
        for n in self._docker_host_list.values():
            w = n.cpu_weight
            weight_sum += w

        period = weight_sum * min_quota
        for n in self._docker_host_list.values():
            n.docker_info['cpu_period'] = period
            n.docker_info['cpu_quota'] = min_quota * n.cpu_weight

        self._cpu_percentage_is_set = True

    def get_host_names(self):
        return [host.name for host in self._docker_host_list.values()]

    def get_host_res_info(self):
        return [get_host_info(host) for host in self._docker_host_list.values()]


class Node(JSONable):
    def __init__(self, name=None, node_type=TYPE_PH, docker_info=None):
        self.name = name
        self.type = node_type
        self.edges = {}
        self.docker_info = merge_info({}, docker_info)
        if 'cpu_weight' in self.docker_info:
            self.cpu_weight = self.docker_info.pop('cpu_weight')
        else:
            self.cpu_weight = 1
        self._neighbor_name_to_edge_id = {}
        self._neighbors = []

    def add_neighbor(self, edge):
        self.edges[edge.edge_id] = edge

    def get_neighbors(self):
        if not self._neighbors:
            for id, edge in self.edges.items():
                if edge.dst_node_name != self.name:
                    self._neighbors.append(edge.dst_node_name)
                else:
                    self._neighbors.append(edge.src_node_name)

        return self._neighbors

    def _init_neighbor_name_to_edge_id(self):
        for edge in self.edges.values():
            if edge.dst_node_name != self.name:
                self._neighbor_name_to_edge_id[edge.dst_node_name] = edge
            else:
                self._neighbor_name_to_edge_id[edge.src_node_name] = edge

    def get_edge_by_neighbor(self, neighbor_name):
        if not self._neighbor_name_to_edge_id:
            # Lazy initialization
            self._init_neighbor_name_to_edge_id()
        return self._neighbor_name_to_edge_id.get(neighbor_name, None)

    def get_cpu_limit(self):
        period = self.docker_info.get('cpu_period', 1)
        quota = self.docker_info.get('cpu_quota', 1)
        return quota / period

    def get_mem_limit(self):
        return self.docker_info.get('mem_limit', None)

    def to_json(self):
        json_obj = {'name': self.name, 'type': self.type, 'edges': {},
                    # 'cpu_period': self.docker_info.get('cpu_period', -1),
                    # 'cpu_quota': self.docker_info.get('cpu_quota', -1),
                    'mem_limit': self.docker_info.get('mem_limit', '-1')}
        if self.cpu_weight:
            json_obj['cpu_weight'] = self.cpu_weight
        for key, value in self.edges.items():
            json_obj['edges'][key] = value.to_json()
        return json.dumps(json_obj)

    def from_json(self, json_str):
        json_obj = json.loads(json_str)
        self.name = json_obj['name']
        self.type = json_obj['type']
        self.cpu_weight = json_obj.get('cpu_weight', 1)

        '''
        if json_obj['cpu_period'] is not -1:
            if not self.docker_info['cpu_period']:
                self.docker_info['cpu_period'] = json_obj['cpu_period']

        if json_obj['cpu_quota'] is not -1:
            if not self.docker_info['cpu_quota']:
                self.docker_info['cpu_quota'] = json_obj['cpu_quota']
        '''

        if json_obj['mem_limit'] is not '-1':
            if 'mem_limit' in self.docker_info:
                self.docker_info['mem_limit'] = json_obj['mem_limit']

        for key, value in json_obj['edges'].items():
            link = Edge()
            link.from_json(value)
            self.edges[key] = link


class Edge(JSONable):
    def __init__(self, src_node_name=None, dst_node_name=None, link_attributes=None):
        if link_attributes is None:
            link_attributes = {}
        self.edge_id = uuid.uuid4().__str__()
        self.src_node_name = src_node_name
        self.dst_node_name = dst_node_name
        self.link_attributes = merge_info({}, link_attributes)

    def get_bw(self):
        return float(self.link_attributes.get('bw', float('Inf')))

    def get_delay(self):
        return self.link_attributes.get('delay', '0ms')

    def to_json(self):
        json_obj = {'edge_id': self.edge_id, 'src_node_name': self.src_node_name,
                    'dst_node_name': self.dst_node_name, 'link_attributes': self.link_attributes}
        return json.dumps(json_obj)

    def from_json(self, json_str):
        json_obj = json.loads(json_str)
        self.edge_id = json_obj['edge_id']
        self.src_node_name = json_obj['src_node_name']
        self.dst_node_name = json_obj['dst_node_name']
        self.link_attributes = json_obj['link_attributes']


class RandomAttributesGenerator:
    def __init__(self, optional_bw, optional_delay, optional_cpu, optional_mem):
        self.optional_bws = optional_bw
        self.optional_delay = optional_delay
        self.optional_cpu = optional_cpu
        self.optional_mem = optional_mem

    def get_random_link_attribute(self):
        rnd_bw = RandomAttributesGenerator.random_in(self.optional_bws)
        rnd_delay = RandomAttributesGenerator.random_in(self.optional_delay)
        link_attr = {"bw": rnd_bw, "delay": rnd_delay}
        return link_attr

    def get_random_host_resources(self):
        rnd_cpu = RandomAttributesGenerator.random_in(self.optional_cpu)
        rnd_mem = RandomAttributesGenerator.random_in(self.optional_mem)
        return {"cpu_weight": rnd_cpu, "mem_limit": rnd_mem}

    @staticmethod
    def random_in(rnd_values):
        values_num = len(rnd_values)
        index = random.randint(0, values_num-1)
        return rnd_values[index]


def random_graph(host_num, switch_num, docker_info=None):
    attr_generator = RandomAttributesGenerator(optional_random_bandwidths, optional_random_delays,
                                               optional_cpu_weights, optional_mem_limits)
    graph, sw_names = tree_graph(switch_num, attr_generator)
    host_names = []
    for i in range(host_num):
        host_names.append("host%s" % (i+1))
        sw_to_connect = random.randint(0, switch_num-1)
        graph.add_node(host_names[i], TYPE_HOST,
                       merge_info(attr_generator.get_random_host_resources(), docker_info))
        link_attributes = attr_generator.get_random_link_attribute()
        graph.connect(host_names[i], sw_names[sw_to_connect], link_attributes)
    return graph, host_names


def generate_ip_for_hosts(host_names):
    import ipaddress
    start_ip = int(ipaddress.IPv4Address('10.0.0.1'))
    num_host = len(host_names)
    host_name_to_ip = {}
    for i in range(num_host):
        host_name_to_ip[host_names[i]] = str(ipaddress.IPv4Address(start_ip+i))
    return host_name_to_ip


def tree_graph(switch_num, attr_generator):
    tgraph = TopoGraph()

    sw_names = []
    for i in range(switch_num):
        sw_names.append("s%s" % (i+1))
        tgraph.add_node(sw_names[i], TYPE_SW)

    for i in reversed(range(1, switch_num)):
        src_index = int((i-1) / 2)
        src_name = sw_names[src_index]
        dst_name = sw_names[i]
        link_attributes = attr_generator.get_random_link_attribute()
        print("src: %s, dst: %s" % (src_name, dst_name))
        tgraph.connect(src_name, dst_name, link_attributes)
    return tgraph, sw_names


def merge_info(info1, info2):
    if not info1 and not info2:
        return {}
    elif not info1:
        return info2
    elif not info2:
        return info1

    info = info1.copy()
    for key, value in info2.items():
        info[key] = value
    return info
