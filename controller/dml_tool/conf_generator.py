import os
import json

from typing import Dict


class Conf:

    def __init__(self, name, **kwargs) -> None:
        for k in kwargs:
            setattr(self, k, kwargs[k])
        self.name = name
        self.connect: dict = {}

    def __hash__(self) -> int:
        return hash(self.name)

    def to_json(self, *args) -> dict:
        conf: dict = {}
        if len(args) == 0:
            args = self.__dict__
        for arg in args:
            # if the arg name does not exist, an exception is thrown
            conf[arg] = getattr(self, arg)
        return conf


class ConfGenerator:

    def __init__(self, dirname, dml_port, node_ip_file, links_file, conf_file) -> None:
        self.node_conf_map: Dict[str, Conf] = {}
        """ A dict storing node conf generated. """

        self.dirname = dirname
        """ Working folder of the generator. """
        self.node_ip: dict = self.__read_json(dirname, node_ip_file)
        """ The node ip read from file. """
        self.links = self.__read_json(dirname, links_file)
        """ The links read from file. """
        self.overall_conf: dict = self.__read_json(dirname, conf_file)
        """ The conf read from file. """
        self.dml_port = dml_port

        self._emulators: Dict[str, Dict[str, list]] = self.node_ip['emulator']
        """ Emulator's name to emulated nodes' [name -> ip+port] kv pairs. """
        self._p_nodes: Dict[str, str] = self.node_ip['physical_node']
        """ Physical node's name -> physical node's ip. """

        self.nodes = self.overall_conf.get('nodes', {})
        for name in self.overall_conf:
            if name != 'nodes':
                setattr(self, name, self.overall_conf[name])

    def gen_conf(self) -> None:
        """ This is the function to be overridden.
        It is used to generate conf files for each of the nodes, including all the information
        the node must be informed of.
        """
        pass

    def gen_connects(self) -> None:
        """
        This function is used to generate connection information (``connect`` part of ``Conf``).
        If you want to do more, override this function.
        Note that this function is executed after ``gen_conf()``, so make sure the ``Conf`` objects
        are created beforehand.
        """
        for name in self.node_conf_map:
            conf = self.node_conf_map[name]
            if name in self.links:
                link_list = self.links[name]
                for link in link_list:
                    dest = link['dest']
                    assert dest not in conf.connect, 'Duplicate link from ' + name + ' to ' + dest
                    conf.connect[dest] = self._node_to_path(dest)

    def save_conf(self, target_folder) -> None:
        for name in self.node_conf_map:
            conf_path = os.path.join(self.dirname, target_folder, name + '_structure.conf')
            with open(conf_path, 'w') as f:
                f.writelines(json.dumps(self.node_conf_map[name].to_json(), indent=2))

    def _node_to_path(self, dst_name):
        """ Node name (physical or emulated) -> ip+port for connection. """
        if dst_name in self._p_nodes:
            return self._p_nodes[dst_name] + ':' + self.dml_port
        else:
            for _, nodes in self._emulators.items():
                if dst_name in nodes.keys():
                    return nodes[dst_name][0] + ":" + str(nodes[dst_name][1])

    # utils?
    def __read_json(self, dirname, filename):
        with open(os.path.join(dirname, filename), 'r') as f:
            return json.loads(f.read().replace('\'', '\"'))


# Example usage

if __name__ == '__main__':
    import argparse
    import importlib
    dirname = os.path.abspath(os.path.dirname(__file__))
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', required=True, type=str, dest='conf_file',
                        help='./relative/path/to/conf/file')
    parser.add_argument('-p', '--dml-port', required=True, type=int, dest='dml_port')
    parser.add_argument('-i', '--node-ip', default='../node_ip.json', type=str, dest='node_ip_file')
    parser.add_argument('-l', '--links', default='../links.json', type=str, dest='links_file')
    parser.add_argument('-t', '--target', default='../dml_file/conf', type=str)

    # using the following, we only need one entry point file
    parser.add_argument('generator')

    args = parser.parse_args()
    module_name, class_name = args.generator.rsplit(".", 1)
    Generator = getattr(importlib.import_module(module_name), class_name)

    generator = Generator(dirname, args.dml_port, args.node_ip_file, args.links_file, args.conf_file)
    generator.gen_conf()
    generator.gen_connects()
    generator.save_conf(args.target)
    