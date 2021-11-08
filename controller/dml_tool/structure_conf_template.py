from conf_generator import ConfGenerator, Conf


# This file is used to generate conf files for each of the nodes in your experiment. It should
# take an overall structure conf file (json), a node ip file (json), a links file (json) as input,
# and produces as output all the information a node should be informed of for each of them.
# General usage:
# 1. Write your overall structure conf json file. Example:
#   {
#       "sync": 15,
#       "nodes": [
#           {"name": "n1-1", "epoch": 1},
#           {"name": "n1-2", "epoch": 1},
#           {"name": "n1-3", "epoch": 1},
#           {"name": "n1-4", "epoch": 1},
#           {"name": "n1-5", "epoch": 1},
#           {"name": "n1-6", "epoch": 1},
#           {"name": "n1-7", "epoch": 1},
#           {"name": "n1-8", "epoch": 1}
#       ]
#   }
# in which 'nodes' are some settings for individual nodes and others are global settings by convention.
# 2. Write your conf generator file (this one)
# 3. Run the conf generator to generate node conf files. For convenience, we provide a single
#    entrypoint in conf_generator.py so that you can generate any conf in one command:
#       python3 conf_generator.py -f <overall_conf_filename> -p <dml_port> YourConfGeneratorClass
#    Take this file for example:
#       python3 conf_generator.py -f <overall_conf_filename> -p <dml_port> structure_conf_template.CustomConfGenerator
# 4. Check the files generated in dml_file folder.


# Normally you don't need to inherit this class. But you can do this if you need to generate conf
# in a complexer manner or looking for better type hints.
# The base conf includes two basic attributes: `name` for the node's name and `connects` to store
# ip+port for all connected nodes.
class CustomConf(Conf):

    def __init__(self, name, **kwargs):
        # setattr() will be called for every entry in kwargs, which has the same effect as manual
        # attribute definition like below (but w/o type hint).
        super().__init__(name, **kwargs)
        self.some_attribute = []
        self.some_intermediate_variable = 0

    # Return a dict containing node conf info, which will then be saved to file. The default is to
    # return all attributes defined in conf (i.e. __dict__).
    def to_json(self, *args) -> dict:
        return {
            'some_attribute': self.some_attribute[0],
            # If you override to_json(), you need to manually include the 'connect' key which should
            # contain ip+port of connected nodes.
            'connect': self.connect
        }


# Customize a ConfGenerator.
class CustomConfGenerator(ConfGenerator):

    # This is the function you are going to override in most cases.
    def gen_conf(self) -> None:
        for node in self.nodes:
            name = node['name']
            # Define a Conf for every node in self.node_conf_map. For this example it initializes
            # the conf object's `some_attribute` to [] and `some_intermediate_variable` to 0.
            custom_conf = self.node_conf_map[name] = CustomConf(name)
            # You can also define (and initialize) the attributes in the constructor like this:
            conf = self.node_conf_map[name] = Conf(name, some_attribute=[], some_intermediate_variable=0)

            # In both ways you can directly access the attributes like the following:
            custom_conf.some_attribute.append('root')
            # noinspection PyUnresolvedReferences
            conf.some_intermediate_variable += 1

    # If you need it, you can override this function for complexer connects management (see the
    # E-Tree Learning (el) example).
    def gen_connects(self) -> None:
        pass

    # Define any other helper function on demand
    def some_helper_foo(self):
        pass

    # You don't need to write code to save the files. The unified entrypoint we provide will call
    # the save function automatically.
