from collections import deque
from conf_generator import ConfGenerator, Conf


class ElConf(Conf):

    def __init__(self, _name, **kwargs):
        super().__init__(_name, **kwargs)
        self.layer = []
        self.father_node = []
        self.child_node = []
        self.child_num = []
        self.curr_child_num = []
        self.sync = []
        self.epoch = 0
        self.forward = {}
        self.n_hop = {}

    def to_json(self, *args) -> dict:
        return {
            'layer': self.layer[::-1],
            'father_node': self.father_node[::-1],
            'child_node': self.child_node[::-1],
            'sync': self.sync[::-1],
            'epoch': self.epoch,
            'connect': self.connect,
            'forward': self.forward
        }


class ElConfGenerator(ConfGenerator):

    def __init__(self, dirname, dml_port, node_ip_file, links_file, conf_file):
        super().__init__(dirname, dml_port, node_ip_file, links_file, conf_file)
        self.father_queue = deque(['top'])
        self.queue = deque([])

    # noinspection PyUnresolvedReferences
    def gen_conf(self) -> None:
        for node in self.nodes:
            name = node['name']
            conf = self.node_conf_map.setdefault(name, ElConf(name))
            conf.layer.append(node['layer'])

            # connect to father node
            father_name = self.father_queue.popleft()
            if father_name == name:
                conf.father_node.append('self')
            elif father_name == 'top':
                conf.father_node.append('top')
            else:
                conf.father_node.append(father_name)

            # let the father node connect to it
            if len(self.queue) != 0:
                # father node.
                u_e = self.node_conf_map[self.queue.popleft()]
                # at the curr-th child nodes set of father node.
                curr = 0
                while u_e.curr_child_num[curr] == u_e.child_num[curr]:
                    curr += 1
                # is the first node of this child nodes set.
                if curr == len(u_e.child_node):
                    u_e.child_node.append([])
                if u_e.name == name:
                    u_e.child_node[curr].append('self')
                else:
                    u_e.child_node[curr].append(name)
                u_e.curr_child_num[curr] += 1

            if 'sync' in node:
                conf.sync.append(node['sync'])
            else:
                conf.sync.append(0)
            if node['layer'] == 1:
                conf.epoch = node['epoch']  # only trainer needs epoch.
                conf.child_node.append([])  # trainer does not have child node.
            else:
                # only aggregator has child node.
                for _ in range(node['child_num']):
                    # let the later [child_num] node be able to call the above
                    # {father_queue.popleft ()} part to connect to it.
                    self.father_queue.append(name)
                    # let the later [child_num] node be able to call the above
                    # {if len (queue) != 0} part to make it connect to the later [child_num] node.
                    self.queue.append(name)
                conf.curr_child_num.append(0)
                conf.child_num.append(node['child_num'])

    # noinspection PyUnresolvedReferences
    def gen_connects(self) -> None:
        for src in self.links:
            conf = self.node_conf_map[src]
            conf.n_hop = {src: 0}  # to itself.
            link_list = self.links[src]
            for link in link_list:
                dest = link['dest']
                assert dest not in conf.connect, Exception('Duplicate link from ' + src + ' to ' + dest)
                conf.connect[dest] = self._node_to_path(dest)
                conf.n_hop[dest] = self._hop_between_nodes(src, dest)

        flag = True
        while flag:
            flag = False
            for i_name in self.node_conf_map:
                node_i = self.node_conf_map[i_name]
                hop1 = node_i.n_hop
                for j_name in node_i.connect:
                    node_j = self.node_conf_map[j_name]
                    if i_name not in node_j.connect:
                        continue
                    hop2 = node_j.n_hop
                    for dest in hop1:
                        hop_num = self._hop_between_nodes(i_name, j_name)
                        if dest not in hop2 or node_j.n_hop[dest] > node_i.n_hop[dest] + hop_num:
                            flag = True
                            node_j.forward[dest] = self._node_to_path(i_name)
                            node_j.n_hop[dest] = node_i.n_hop[dest] + hop_num

    def _hop_between_nodes(self, node1, node2):
        if node1 in self._p_nodes or node2 in self._p_nodes:
            return 1
        # try to use the emulated node from the same emulator when need the same hop for forwarding.
        if self._node_to_emulator_ip(node1) == self._node_to_emulator_ip(node2):
            return 0.99
        return 1

    def _node_to_emulator_ip(self, node):
        for _, nodes in self._emulators.items():
            if node in nodes.keys():
                return nodes[node][0]
