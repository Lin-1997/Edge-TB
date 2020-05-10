import uuid
import json

from graph import JSONable, TYPE_PH, TYPE_SW, TYPE_HOST


class TopoGraph(JSONable):
    def __init__(self):
        self._node_list = {}

    def add_node(self, name, node_type):
        if name not in self._node_list:
            self._node_list[name] = Node(name, node_type)

    def connect(self, src_name, src_type, dst_name, dst_type, link_attributes):
        if src_name not in self._node_list:
            self.add_node(src_name, src_type)
        if dst_name not in self._node_list:
            self.add_node(dst_name, dst_type)

        if src_name not in self._node_list and dst_name not in self._node_list:
            src_node = self._node_list.get(src_name)
            # dst_node = self._node_list.get(dst_name)
            link = Edge(src_name, dst_name, link_attributes)
            src_node.add_neighbor(link)
        else:
            # log error
            pass

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

    def build_nodes(self, net, name2ip, docker_info):
        net_node_list = {}
        for node_name, node in self._node_list.items():
            if node.type == TYPE_HOST:
                host = net.addDocker(node_name, name2ip[node_name], **docker_info)
                net_node_list[node_name] = host
            elif node.type == TYPE_SW:
                sw = net.addSwitch(node_name)
                net_node_list[node_name] = sw
            else:
                # log error
                pass
        self.build_edges(net, net_node_list)

    def build_edges(self, net, node_name2node):
        for node in self._node_list.values():
            for edge in node.out_edges.values():
                src = edge.src_node_name
                dst = edge.dst_node_name
                src_node = node_name2node[src]
                dst_node = node_name2node[dst]
                net.addLink(src_node, dst_node, **edge.link_attributes)


class Node(JSONable):
    def __init__(self, sw_name=None, node_type=TYPE_PH):
        self._name = sw_name
        self.type = node_type
        self.out_edges = {}

    def add_neighbor(self, out_edge):
        self.out_edges[out_edge.edge_id] = out_edge

    def to_json(self):
        json_obj = {'name': self._name, 'type': self.type, 'out_edges': {}}
        for key, value in self.out_edges.items():
            json_obj['out_edges'][key] = value.to_json()
        return json.dumps(json_obj)

    def from_json(self, json_str):
        json_obj = json.loads(json_str)
        self._name = json_obj['name']
        self.type = json_obj['type']
        for key, value in json_obj['out_edges'].items():
            link = Edge()
            link.from_json(value)
            self.out_edges[key] = link


class Edge(JSONable):
    def __init__(self, src_node_name=None, dst_node_name=None, link_attributes=None):
        if link_attributes is None:
            link_attributes = {}
        self.edge_id = uuid.uuid4()
        self.src_node_name = src_node_name
        self.dst_node_name = dst_node_name
        self.link_attributes = link_attributes

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
