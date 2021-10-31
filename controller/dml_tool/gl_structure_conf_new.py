from conf_generator import ConfGenerator, Conf


class GlConfGenerator(ConfGenerator):

    # noinspection PyUnresolvedReferences, SpellCheckingInspection
    def gen_conf(self) -> None:
        for node in self.nodes:
            name = node['name']
            assert name not in self.node_conf_map, 'Duplicate node: ' + name
            self.node_conf_map[name] = Conf(name, sync=self.sync, epoch=node['epoch'])
