from flask import request
from role_base import Role


class CustomRole(Role):

    # For convenience and better code reuse, we recommend that every global variable should be
    # defined as instance attribute. You can define them anywhere you want, but make sure to avoid
    # referencing before definition.
    # You can also define them again as class attributes for better type hinting, but it is purely
    # optional.
    some_current_status: int

    def load_actions(self) -> None:
        super().load_actions()

        # To add any custom action, you need to override the function load_actions(). There are
        # several pre-defined actions such as '/hi' for Docker heartbeat (called by Docker) and
        # '/conf' for receiving conf files from the controller (called by yourself).
        # You can call super() first to load them (just like above), or re-define them yourself
        # here.

        @self.app.route('/foo3', methods=['POST'])
        def route_foo():
            some_param = request.args.get('param_name', type=str)
            self.on_route_foo3()
            return ''   # make sure to have a return value, set to '' if not needed

        @self.app.route('foo4', methods=['GET'])
        def route_foo2():
            # You can make use of the thread pool executor for async execution.
            self.executor.submit(self.on_route_foo4)    # no need to pass self
            return ''

    # Define any function that does the work (e.g. train the model or perform aggregation)

    def on_route_foo3(self):
        pass

    def on_route_foo4(self):
        pass

    # Or you can also make use of the hooks for pre-defined actions
    def _hook_handle_structure(self) -> None:
        self.some_current_status = 0  # init an instance attribute (basically act as global variable)


# Define the entry point for execution. Here is an example which you can make use of by few code
# modifications.
if __name__ == '__main__':
    import argparse
    import os
    from nns.nn_fashion_mnist import nn

    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', type=str, help='App host', default='0.0.0.0')
    parser.add_argument('-p', '--port', type=int, help='DML port', default=3333)
    args = parser.parse_args()

    dirname = os.path.abspath(os.path.dirname(__file__))
    # Change the CustomRole to the role class you defined, and if you wish, change the dataset path
    # and log path.
    role = CustomRole(dirname, nn,
                      os.path.join(dirname, '../dataset/FASHION_MNIST/train_data'),
                      os.path.join(dirname, '../dataset/FASHION_MNIST/test_data'),
                      os.path.abspath(os.path.join(dirname, '../dml_file/log/')))
    role.run(host=args.host, port=args.port)

    # Example command to run: python3 role_template.py -p 3333
