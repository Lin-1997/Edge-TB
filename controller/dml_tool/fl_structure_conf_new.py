from conf_generator import ConfGenerator, Conf


class FlConfGenerator(ConfGenerator):

    # noinspection PyUnresolvedReferences
    def gen_conf(self) -> None:
        # for this example we take the first node as aggregator and the rest as trainers
        aggregator = self.nodes[0]
        aggregator_name = aggregator['name']
        aggregator_conf = self.node_conf_map[aggregator_name] = \
            Conf(aggregator_name, trainer_fraction=aggregator['trainer_fraction'], sync=aggregator['sync'],
                 child_node=[])

        for i in range(1, len(self.nodes)):
            trainer = self.nodes[i]
            trainer_name = trainer['name']
            self.node_conf_map[trainer_name] = Conf(trainer_name, epoch=trainer['epoch'], father_node=[aggregator_name])
            aggregator_conf.child_node.append(trainer_name)
