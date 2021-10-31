from controller_base import Controller
from manager_base import RuntimeManager


class GlRuntimeManager(RuntimeManager):
    pass


if __name__ == '__main__':
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='AppConfig yaml file', required=True)
    args = parser.parse_args()

    dirname = os.path.abspath(os.path.dirname(__file__))
    controller = Controller(dirname)
    controller.init(os.path.join(dirname, args.config))
    controller.set_runtime_manager(GlRuntimeManager(dirname))
    controller.run()
